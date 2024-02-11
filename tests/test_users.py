from src.data_classes.users import UserRegisterData


def test_user_registration(client, cleanup_after_test):
    test_email = "test@test.com"
    request = UserRegisterData(email=test_email, password="string")
    response = client.post(url="/register", json=request.dict())
    assert response.status_code == 201
    json_response = response.json()
    assert json_response["message"] == (
        f"User with {test_email} successfully register"
    )


def test_user_login(client, cleanup_after_test):
    # для начала надо зарегистрировать пользователя
    test_email = "test@test.com"
    password = "string"
    request = UserRegisterData(email=test_email, password=password)
    response = client.post(url="/register", json=request.dict())
    assert response.status_code == 201
    json_response = response.json()
    assert json_response["message"] == (
        f"User with {test_email} successfully register"
    )
    # логинимся зарегестрированным пользователем
    request = {"username": test_email, "password": password}
    response = client.post("/auth", data=request)
    assert response.status_code == 200
    json_response = response.json()
    assert "access_token" in json_response
    assert "token_type" in json_response
