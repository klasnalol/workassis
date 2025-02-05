import json

from src.base import MessageWrapper

from flask import Blueprint, request, render_template, current_app

from ollama import chat, ChatResponse

from pydantic import BaseModel

text_voice_filter_bp = Blueprint('text-voice-filter', __name__, template_folder='templates', url_prefix='/api')

message_wrapper = MessageWrapper()


class ResponseProduct(BaseModel):
    name: str
    price: float
    category: str
    available: bool
    description: str
    additional_info: str | None


class ResponseProductList(BaseModel):
    products: list[ResponseProduct]


def ollama_search(query: str, messages: MessageWrapper | None = None):
    response: ChatResponse = chat(
            model="filter",
            messages=[{
                'role': 'usr',
                'content': query
            }],
            format=ResponseProductList.model_json_schema(),
        )
    return response


@text_voice_filter_bp.route('/text-voice-filter', method=["POST", "GET"])
def text_voice_filter():
    req = request.get_json()
    # products = ollama_search()
    return render_template("base.html") 
