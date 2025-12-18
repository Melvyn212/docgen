"""
Client Python minimal pour générer et récupérer un PDF via l'API.
Prérequis : pip install requests
Usage :
  python client_example.py --host http://127.0.0.1:8000 --user admin --password secret --student 1 --term T1 --type bulletin
"""

import argparse
import time
import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://127.0.0.1:8000")
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--student", type=int, required=True)
    parser.add_argument("--term", default="T1")
    parser.add_argument(
        "--type",
        choices=["bulletin", "honor"],
        default="bulletin",
        help="bulletin or honor (tableau d'honneur)",
    )
    parser.add_argument("--output", default="document.pdf")
    args = parser.parse_args()

    session = requests.Session()
    # Auth basique pour l'exemple (pour la prod, préférer token/JWT)
    session.auth = (args.user, args.password)

    endpoint = "/api/documents/bulletin/" if args.type == "bulletin" else "/api/documents/honor-board/"
    resp = session.post(
        f"{args.host}{endpoint}",
        json={"student_id": args.student, "term": args.term},
    )
    resp.raise_for_status()
    doc_id = resp.json()["id"]
    print(f"Demande créée, id={doc_id}, status={resp.json()['status']}")

    # Polling simple jusqu'à READY
    for _ in range(30):
        r = session.get(f"{args.host}/api/documents/{doc_id}/download/")
        if r.status_code == 200:
            payload = r.json()
            if payload.get("path"):
                # suppose stockage local accessible via chemin ou URL
                pdf_resp = session.get(payload["path"])
                if pdf_resp.status_code == 200 and pdf_resp.headers.get("content-type") == "application/pdf":
                    with open(args.output, "wb") as f:
                        f.write(pdf_resp.content)
                    print(f"PDF téléchargé dans {args.output}")
                    return
                else:
                    # path peut être un chemin local : à adapter selon storage
                    print(f"URL PDF : {payload['path']} (à récupérer manuellement)")
                    return
        time.sleep(2)
    print("Timeout avant que le document soit prêt.")


if __name__ == "__main__":
    main()
