from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from time import time
import json
import httpx


app = FastAPI()
http_client = httpx.AsyncClient(verify=False, timeout=30)
token_dict = dict()


@app.on_event("shutdown")
async def on_shutdown():
    await http_client.aclose()
    print('app is shut down.')


async def get_access_token(delta: int, token_dict):
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"

    payload = {
        'scope': 'GIGACHAT_API_PERS'
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': 'b3fa0992-37a4-4196-bf1a-ea29382cb88f',
        'Authorization': 'Basic NThkYzBjNTktZjY3ZS00ZGU2LWI0OTUtN2RlYzMzYzAxMDgxOjU5M2UzZmZhLTlmYjktNGM5MS1iMDkyLWNjNTE1YWFmMGIxYg=='
    }
    if len(token_dict) == 0 or time() - token_dict['creation_time'] > delta:
        response = await http_client.post(url, headers=headers, data=payload)
        token = json.loads(response.text)['access_token']
        token_dict = {'token': token, 'creation_time': time()}

    return token_dict['token']


available_models = ["GigaChat-Pro", "GigaChat"]
model_pro = "GigaChat-Pro"
model_simple = "GigaChat"
api_url = 'https://gigachat.devices.sberbank.ru/api/v1/chat/completions'


class ChatItem(BaseModel):
    role: str = ""
    content: str = ""


class RequestData(BaseModel):
    model: str = model_simple
    messages: List[ChatItem]
    n: int = 1
    stream: bool = False
    max_tokens: int = 512
    repetition_penalty: float = 1
    update_interval: float = 1


class GenerateRequestData(BaseModel):
    prompt: str = ""
    max_tokens: int = 512


async def generate_routine(prompt: str, model: str, access_token: str, max_tokens: int = 512):
    assert model in available_models
    chat_item = ChatItem(role='user', content=prompt)
    messages = [chat_item]
    request_data = RequestData(model=model, messages=messages, max_tokens=max_tokens)
    authorization = f'Bearer {access_token}'
    headers = {'Authorization': authorization}
    resp = await http_client.post(api_url, content=request_data.json(), headers=headers)

    return json.loads(resp.text)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/generate")
async def generate(request_data: GenerateRequestData):
    access_token = await get_access_token(30, token_dict)
    resp = await generate_routine(request_data.prompt, model_pro, access_token, max_tokens=request_data.max_tokens)

    return resp["choices"][0]['message']['content']


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
