import requests
import keyring

token = keyring.get_password("aresta_editor", "github_token")
headers = {"Authorization": f"Bearer {token}"} if token else {}
res = requests.get('https://api.github.com/repos/aresta-climb/aresta_db/pulls/2/files', headers=headers)
data = res.json()
if isinstance(data, dict) and 'message' in data:
    print(data['message'])
else:
    for f in data[:10]:
        print(f"{f['status']}: {f.get('previous_filename', '')} -> {f['filename']}")
