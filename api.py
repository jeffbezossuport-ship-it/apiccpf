import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify

LOGIN_URL = "https://sisregiii.saude.gov.br/"
CADWEB_URL = "https://sisregiii.saude.gov.br/cgi-bin/cadweb50"

USER = "pontes.tatianesol"
PASS_HASH = "30a7fc9ecc375787c8ab8a3350fd70018d9a60ed15f20271abef252b99f3bce1"

app = Flask(__name__)


def get_session():
    s = requests.Session()

    data = {
        "usuario": USER,
        "senha": "",
        "senha_256": PASS_HASH,
        "etapa": "ACESSO",
        "logout": ""
    }

    r = s.post(
        LOGIN_URL,
        data=data,
        timeout=15
    )

    print("STATUS LOGIN:", r.status_code)
    print("URL LOGIN:", r.url)

    with open("login_debug.html", "w", encoding="utf-8") as f:
        f.write(r.text)

    # abre a tela igual o navegador faz
    s.get(
        "https://sisregiii.saude.gov.br/cgi-bin/cadweb50?standalone=1",
        timeout=15
    )

    return s


def extrair_dados(html):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    dados = {
        "pessoais": {},
        "documentos": {},
        "endereco": {},
        "contatos": [],
        "cadastro": {}
    }

    trs = soup.find_all("tr")

    try:

        for i, tr in enumerate(trs):

            texto = tr.get_text(" ", strip=True)

            # CNS
            if "CNS:" in texto and i + 1 < len(trs):
                dados["pessoais"]["cns"] = trs[i + 1].get_text(" ", strip=True)

            # Nome
            elif "Nome:" in texto and "Nome Social" in texto and i + 1 < len(trs):
                cols = trs[i + 1].find_all("td")
                if len(cols) >= 2:
                    dados["pessoais"]["nome"] = cols[0].get_text(strip=True)
                    dados["pessoais"]["nome_social"] = cols[1].get_text(strip=True)

            # Mãe / Pai
            elif "Nome da M" in texto and i + 1 < len(trs):
                cols = trs[i + 1].find_all("td")
                if len(cols) >= 2:
                    dados["pessoais"]["nome_mae"] = cols[0].get_text(strip=True)
                    dados["pessoais"]["nome_pai"] = cols[1].get_text(strip=True)

            # Sexo / Raça
            elif "Sexo:" in texto and "Ra" in texto and i + 1 < len(trs):
                cols = trs[i + 1].find_all("td")
                if len(cols) >= 2:
                    dados["pessoais"]["sexo"] = cols[0].get_text(strip=True)
                    dados["pessoais"]["raca"] = cols[1].get_text(strip=True)

            # Nascimento / Sangue
            elif "Data de Nascimento:" in texto and i + 1 < len(trs):
                cols = trs[i + 1].find_all("td")
                if len(cols) >= 2:
                    dados["pessoais"]["nascimento"] = cols[0].get_text(strip=True)
                    dados["pessoais"]["tipo_sanguineo"] = cols[1].get_text(strip=True)

            # Nacionalidade / Município Nascimento
            elif "Nacionalidade:" in texto and i + 1 < len(trs):
                cols = trs[i + 1].find_all("td")
                if len(cols) >= 2:
                    dados["pessoais"]["nacionalidade"] = cols[0].get_text(strip=True)
                    dados["pessoais"]["municipio_nascimento"] = cols[1].get_text(strip=True)

            # Tipo Logradouro / Logradouro
            elif "Tipo Logradouro:" in texto and i + 1 < len(trs):
                cols = trs[i + 1].find_all("td")
                if len(cols) >= 2:
                    dados["endereco"]["tipo_logradouro"] = cols[0].get_text(strip=True)
                    dados["endereco"]["logradouro"] = cols[1].get_text(strip=True)

            # Complemento / Número
            elif "Complemento:" in texto and "Número:" in texto and i + 1 < len(trs):
                cols = trs[i + 1].find_all("td")
                if len(cols) >= 2:
                    dados["endereco"]["complemento"] = cols[0].get_text(strip=True)
                    dados["endereco"]["numero"] = cols[1].get_text(strip=True)

            # Bairro / CEP
            elif "Bairro:" in texto and "CEP:" in texto and i + 1 < len(trs):
                cols = trs[i + 1].find_all("td")
                if len(cols) >= 2:
                    dados["endereco"]["bairro"] = cols[0].get_text(strip=True)
                    dados["endereco"]["cep"] = cols[1].get_text(strip=True)

            # País / Município
            elif "País de Residência:" in texto and i + 1 < len(trs):
                cols = trs[i + 1].find_all("td")
                if len(cols) >= 2:
                    dados["endereco"]["pais"] = cols[0].get_text(strip=True)
                    dados["endereco"]["municipio"] = cols[1].get_text(strip=True)

            # CPF
            elif "CPF:" in texto and i + 1 < len(trs):
                dados["documentos"]["cpf"] = trs[i + 1].get_text(" ", strip=True)

        # TELEFONES
        for tr in trs:

            cols = tr.find_all("td")

            if len(cols) == 3:

                tipo = cols[0].get_text(strip=True)

                if tipo == "CELULAR":

                    dados["contatos"].append({
                        "tipo": tipo,
                        "ddd": cols[1].get_text(strip=True),
                        "numero": cols[2].get_text(strip=True)
                    })

        # RG
        for tr in trs:

            cols = tr.find_all("td")

            if len(cols) == 4:

                rg = cols[0].get_text(strip=True)

                if rg.isdigit():

                    dados["documentos"]["rg"] = rg
                    dados["documentos"]["orgao_emissor"] = cols[1].get_text(strip=True)
                    dados["documentos"]["estado_emissor"] = cols[2].get_text(strip=True)
                    dados["documentos"]["data_emissao"] = cols[3].get_text(strip=True)

                    break

        # Qualidade da ficha
        body = soup.get_text(" ", strip=True)

        import re

        qualidade = re.search(
            r'Grau de qualidade das informacoes:\s*(\d+%)',
            body
        )

        if qualidade:
            dados["cadastro"]["qualidade"] = qualidade.group(1)

        atualizacao = re.search(
            r'Ultima atualizacao junto ao CADWEB:\s*([0-9/]+\s*@\s*[0-9:]+)',
            body
        )

        if atualizacao:
            dados["cadastro"]["ultima_atualizacao"] = atualizacao.group(1)

    except Exception as e:
        print("ERRO PARSER:", str(e))

    return dados


@app.route("/consulta-cpf", methods=["GET"])
def api_cpf():

    cpf_raw = request.args.get("cpf")

    if not cpf_raw:
        return jsonify({
            "erro": "CPF não informado"
        }), 400

    cpf_clean = "".join(filter(str.isdigit, cpf_raw))

    if len(cpf_clean) != 11:
        return jsonify({
            "erro": "CPF inválido"
        }), 400

    try:

        sess = get_session()

        payload = {
            "nu_cns": cpf_clean,
            "nome_paciente": "",
            "nome_mae": "",
            "dt_nascimento": "",
            "uf_nasc": "",
            "mun_nasc": "",
            "uf_res": "",
            "mun_res": "",
            "sexo": "",
            "etapa": "DETALHAR",
            "url": "",
            "standalone": "1"
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
            "Origin": "https://sisregiii.saude.gov.br",
            "Referer": "https://sisregiii.saude.gov.br/cgi-bin/cadweb50?standalone=1",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        print("\nPAYLOAD:", payload)
        print("COOKIES:", sess.cookies.get_dict())

        r = sess.post(
            CADWEB_URL,
            params={"standalone": "1"},
            data=payload,
            headers=headers,
            timeout=30
        )

        print("\n" + "=" * 120)
        print("STATUS:", r.status_code)
        print("URL FINAL:", r.url)
        print("COOKIES:", sess.cookies.get_dict())
        print("=" * 120)
        print(r.text[:5000])
        print("=" * 120 + "\n")

        with open(
            "consulta_debug.html",
            "w",
            encoding="utf-8"
        ) as f:
            f.write(r.text)

        if "Erro de sincronizacao" in r.text:
            return jsonify({
                "erro": "Erro de sincronização do SISREG",
                "status": r.status_code
            }), 500

        if "CONSULTA AO CADASTRO" not in r.text:
            return jsonify({
                "erro": "Página inesperada retornada pelo SISREG",
                "status": r.status_code,
                "url": r.url
            }), 500

        return jsonify(
            extrair_dados(r.text)
        )

    except Exception as e:

        import traceback

        print("\nERRO COMPLETO:")
        traceback.print_exc()

        return jsonify({
            "erro": str(e)
        }), 500


if __name__ == "__main__":
    print(
        "Rodando em http://127.0.0.1:5000/consulta-cpf?cpf=58544470963"
    )

    app.run(
        host="0.0.0.0",
        port=5000
    )