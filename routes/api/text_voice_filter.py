from flask import Blueprint, request, render_template, current_app

from ollama import chat, ChatResponse

from pydantic import BaseModel

text_voice_filter_bp = Blueprint('products-voice-filter', __name__, template_folder='templates', url_prefix='/api')

class ResponseProduct(BaseModel):
    name: str
    price: float
    category: str
    available: bool
    description: str
    additional_info: str | None

class ResponseProductList(BaseModel):
    products: list[ResponseProduct]

def ollama_search(query: str):
    response: ChatResponse = chat(
            model="filter", 
            messages = [
                {
                    'role': 'user',
                    'content': query
                }
            ],
            format=ResponseProductList.model_json_schema(),
        )

@text_voice_filter_bp.route('/text-voice-filter', method=["POST"])
def text_voice_filter():
    req = request.get_json()
    print(req)
    pass
