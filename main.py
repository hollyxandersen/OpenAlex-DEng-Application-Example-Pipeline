
import requests

url = "https://api.openalex.org/works"

params = {
    "search": "photoactive battery",
    "per_page": 10
}

response = requests.get(url, params=params, timeout=30)

print("Status code:", response.status_code)

response.raise_for_status()

data = response.json()

print("Total matching works:", data["meta"]["count"])
print("Works returned:", len(data["results"]))

for work in data["results"]:
    print(work["title"])
