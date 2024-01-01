import requests

# url = "http://localhost:5000/"

def get_all_room_test(base_url):
    url = base_url + "get_all_room/"
    response = requests.get(url)
    print(response.content)

def get_room_test(base_url, data, room_id):
    url = base_url + "get_room/"
    data["room_id"] = room_id
    response = requests.get(url, params=data)
    print(response.content)
    
def join_private_room_test(base_url, data, room_id):
    url = base_url + "join_private/"
    data["room_id"] = room_id
    response = requests.post(url, data=data)
    print(response.content)
    
def join_public_room_test(base_url, data):
    url = base_url + "join_public/"
    response = requests.post(url, data=data)
    print(response.content)
    
def update_room_test(base_url, data):
    url = base_url + "update_room/"
    response = requests.post(url, data=data)
    print(response.content)
    
    
def create_room_test(base_url, data):
    url = base_url + "create_room/"
    response = requests.post(url, data=data)
    print(response.content)
    
def leave_room(base_url, data):
    url = base_url + "leave_room/"
    response = requests.post(url, data=data)
    print(response.content)
        
if __name__ == "__main__":
    url = "http://localhost:5000/"
    data0 = {
        "guid": "test-abcdef",
        "name": "test_client",
        "game_type": "public",
        "room_id": "-Nn3MbsrKsDQQWZoDDYk",
        "IP_endpoint": "192.168.0.1:5001",
        "start_game": True
    }
    data1 = {
        "guid": "test-ghijkl",
        "name": "test_client_B",
        "game_type": "public",
        "room_id": "-Nn3MbsrKsDQQWZoDDYk",
        "IP_endpoint": "192.168.0.1:5000"
    }
    # get_all_room_test(url)
    # join_private_room_test(url, data1, "-Nn3MbsrKsDQQWZoDDYk")
    # leave_room(url, data1)
    # create_room_test(url, data)
    # get_room_test(guid, "-NflOvgTTD_SqYJf9h9T")
    update_room_test(url, data0)