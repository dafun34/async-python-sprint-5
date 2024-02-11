import os
from unittest.mock import AsyncMock

from passlib.handlers.bcrypt import bcrypt

from src.clients.s3 import S3Client
from src.core.config import get_settings
from src.data_classes.files import FileItem
from src.data_classes.users import UserRegisterData
from src.models.file import File
from src.models.user import User
from src.services.files import FilesService

settings = get_settings()


def test_upload_file(client, monkeypatch, cleanup_after_test):
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
    response_json = response.json()
    headers = {"Authorization": f"Bearer {response_json['access_token']}"}
    mock_response_data_one = {
        "ResponseMetadata": {
            "RequestId": "17B512C61013C9CB",
            "HTTPStatusCode": 200,
            "HTTPHeaders": {},
            "RetryAttempts": 0,
        },
        "ContentLength": 5,
    }
    mock_response_data_two = {
        "ResponseMetadata": {
            "RequestId": "17B512C61013C9CB",
            "HTTPStatusCode": 200,
            "HTTPHeaders": {},
            "RetryAttempts": 0,
        },
        "ContentLength": 100,
    }
    object_exist_mock = AsyncMock()
    # первая обращение в minio возвращает, то что объект не создан и нет метадаты
    # второе обращение говорит, что объект существует и возвращает метадату
    object_exist_mock.side_effect = [
        (False, {}),
        (True, mock_response_data_one),
        (True, mock_response_data_one),
        (True, mock_response_data_two),
    ]
    put_object = AsyncMock()
    monkeypatch.setattr(S3Client, "object_exists", object_exist_mock)
    # мокаем запись объекта в хранилище минио, put_object ничего не возвращает
    monkeypatch.setattr(S3Client, "put_object", put_object)
    filename = "example.txt"
    example_filepath = os.path.join(settings.tests_dir, filename)
    path = "temp"
    with open(example_filepath, "rb") as file:
        response = client.post(
            "files/upload",
            files={"file": (filename, file.read())},
            data={"path": path},
            headers=headers,
        )
    assert response.status_code == 201
    response_json = response.json()
    assert response_json["name"] == filename
    assert response_json["path"] == f"{test_email}/{path}/{filename}"
    assert response_json["is_downloadable"] is True
    assert response_json["size"] == mock_response_data_one["ContentLength"]
    # попробуем перезаписать тот же самый файл, но уже большего размера
    put_object = AsyncMock()
    # мокаем запись объекта в хранилище минио, put_object ничего не возвращает
    monkeypatch.setattr(S3Client, "put_object", put_object)
    path = "temp"
    with open(example_filepath, "rb") as file:
        response = client.post(
            "files/upload",
            files={"file": (filename, file.read())},
            data={"path": path},
            headers=headers,
        )
    assert response.status_code == 201
    response_json = response.json()
    assert response_json["name"] == filename
    assert response_json["path"] == f"{test_email}/{path}/{filename}"
    assert response_json["is_downloadable"] is True
    assert response_json["size"] == mock_response_data_two["ContentLength"]


def test_get_files(client, cleanup_after_test, sync_session):
    # создаем тестового юзера через БД
    test_email = "test@test.com"
    test_pass = "testpass"
    user_object = User(email=test_email, password=bcrypt.hash(test_pass))
    sync_session.add(user_object)
    sync_session.commit()

    # создаем 10 записей о загруженных файлах в БД
    # файлы загружены одним пользователем
    for num in range(1, 10 + 1):
        filename = f"example{num}.txt"
        file_object = File(
            account_id=user_object.email,
            path=f"{user_object.email}/test/{filename}",
            size=num,
            name=filename,
        )
        sync_session.add(file_object)
        sync_session.commit()

    # получаем все созданные файлы из БД и создаем словарь
    # который потом сравниваем с ответом
    dict_all_files_from_db = []
    all_files_from_db = sync_session.query(File).all()
    for file_object in all_files_from_db:
        dict_all_files_from_db.append(
            FileItem.model_validate(
                FilesService.check_download_permissions(
                    file_object, user_object
                )
            ).model_dump(mode="json")
        )
    # логинемся и получаем токен для тестового юзера
    request = {"username": test_email, "password": test_pass}
    response = client.post("/auth", data=request)
    assert response.status_code == 200
    response_json = response.json()
    headers = {"Authorization": f"Bearer {response_json['access_token']}"}
    response = client.get("/files/files", headers=headers)
    response_json = response.json()
    assert response_json == dict_all_files_from_db


def test_get_download_link(
    client, cleanup_after_test, sync_session, monkeypatch
):
    # создаем тестового юзера через БД
    test_email = "test@test.com"
    test_pass = "testpass"
    user_object = User(email=test_email, password=bcrypt.hash(test_pass))
    sync_session.add(user_object)
    sync_session.commit()
    # создаем тестовую запись о файле
    filename = "example.txt"
    size = 100500
    file_object = File(
        account_id=user_object.email,
        path=f"{user_object.email}/test/{filename}",
        size=size,
        name=filename,
    )
    sync_session.add(file_object)
    sync_session.commit()

    # логинемся и получаем токен для тестового юзера
    request = {"username": test_email, "password": test_pass}
    response = client.post("/auth", data=request)
    assert response.status_code == 200
    response_json = response.json()
    headers = {"Authorization": f"Bearer {response_json['access_token']}"}
    # мокаем запрос в minio
    get_download_link = AsyncMock()
    get_download_link.side_effect = [
        f"{settings.s3_protocol}://{settings.s3_host}:{settings.s3_port}/{filename}",
        f"{settings.s3_protocol}://{settings.s3_host}:{settings.s3_port}/{filename}",
        f"{settings.s3_protocol}://{settings.s3_host}:{settings.s3_port}/{filename}",
    ]
    monkeypatch.setattr(S3Client, "get_download_url", get_download_link)
    response = client.get(
        "/files/download", headers=headers, params={"path": file_object.path}
    )
    assert response.status_code == 200
    response_json = response.json()
    assert (
        response_json["download_link"]
        == f"{settings.s3_protocol}://{settings.host}:{settings.s3_port}/{filename}"
    )
    # попытаемся сделать запрос передав в качестве path идентификатор файла
    response = client.get(
        "/files/download", headers=headers, params={"path": file_object.id}
    )
    assert response.status_code == 200
    response_json = response.json()
    assert (
        response_json["download_link"]
        == f"{settings.s3_protocol}://{settings.host}:{settings.s3_port}/{filename}"
    )
    # создадим нового пользователя авторизуемся и попробуем скачать тот же файл
    # создаем тестового юзера через БД
    test_email = "test_another@test.com"
    test_pass = "testpass"
    user_object = User(email=test_email, password=bcrypt.hash(test_pass))
    sync_session.add(user_object)
    sync_session.commit()
    # логинемся и получаем токен для тестового юзера
    request = {"username": test_email, "password": test_pass}
    response = client.post("/auth", data=request)
    assert response.status_code == 200
    response_json = response.json()
    headers = {"Authorization": f"Bearer {response_json['access_token']}"}
    # попытаемся сделать запрос передав в качестве path идентификатор файла
    response = client.get(
        "/files/download", headers=headers, params={"path": file_object.id}
    )
    assert response.status_code == 403
    response_json = response.json()
    assert response_json == "У вас нет прав на скачивания этого файла"
