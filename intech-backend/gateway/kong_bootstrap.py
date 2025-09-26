import requests
import time

KONG_ADMIN_URL = "http://kong:8001"

SERVICES = [
    {
        "name": "auth",
        "url": "http://auth:8000",
        "routes": ["/auth"],
        "plugins": ["rate-limiting"],
    },
    {
        "name": "accounts",
        "url": "http://accounts:8001",
        "routes": ["/accounts"],
        "plugins": ["rate-limiting"],
    },
    {
        "name": "transactions",
        "url": "http://transactions:8002",
        "routes": ["/transactions"],
        "plugins": ["rate-limiting"],
    },
]


def create_or_update_service(service):
    r = requests.get(f"{KONG_ADMIN_URL}/services/{service['name']}")
    if r.status_code == 200:
        print(f"Service {service['name']} exists, updating...")
        r = requests.patch(
            f"{KONG_ADMIN_URL}/services/{service['name']}",
            data={"url": service["url"]},
        )
    else:
        print(f"Creating service {service['name']}...")
        r = requests.post(
            f"{KONG_ADMIN_URL}/services",
            data={"name": service["name"], "url": service["url"]},
        )

    if r.status_code not in (200, 201):
        print(f"Error creating/updating service {service['name']}: {r.text}")


def create_route(service_name, path):
    r = requests.post(
        f"{KONG_ADMIN_URL}/services/{service_name}/routes",
        data={"paths[]": path, "strip_path": "true"},
    )
    if r.status_code == 201:
        print(f"Route {path} created for {service_name}")
    elif r.status_code == 409:
        print(f"Route {path} already exists for {service_name}")
    else:
        print(f"Error creating route {path} for {service_name}: {r.text}")


def add_plugin(service_name, plugin):
    data = {"name": plugin}
    if plugin == "rate-limiting":
        data.update({"config.minute": 100, "config.policy": "local"})
    r = requests.post(f"{KONG_ADMIN_URL}/services/{service_name}/plugins", data=data)
    if r.status_code == 201:
        print(f"Plugin {plugin} added to {service_name}")
    elif r.status_code == 409:
        print(f"Plugin {plugin} already exists on {service_name}")
    else:
        print(f"Error adding plugin {plugin} to {service_name}: {r.text}")


def bootstrap():
    print("Waiting for Kong admin to be ready...")
    while True:
        try:
            r = requests.get(f"{KONG_ADMIN_URL}/")
            if r.status_code == 200:
                print("Kong admin is ready!")
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(2)

    for service in SERVICES:
        create_or_update_service(service)
        for path in service.get("routes", []):
            create_route(service["name"], path)
        for plugin in service.get("plugins", []):
            add_plugin(service["name"], plugin)


if __name__ == "__main__":
    bootstrap()
