from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import io, docx, torch
from PyPDF2 import PdfReader
from starlette.responses import StreamingResponse
import urllib.parse
from typing import Dict

app = FastAPI()

# 挂载静态文件和模板
app.mount("/static", StaticFiles(directory="templates"), name="static")
templates = Jinja2Templates(directory="templates")

# 加载全局模型（只用一个超强小模型搞定全球200+语言）
MODEL_NAME = "facebook/nllb-200-distilled-600M"
tokenizer = None
model = None


def get_nllb_model():
    global tokenizer, model
    if model is None:
        print("首次加载 NLLB-600M 模型，大概30秒左右，请稍等…")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
        # 如果你有显卡，自动用GPU；没有就用CPU
        if torch.cuda.is_available():
            model = model.cuda()
    return tokenizer, model


# 语言代码映射（前端显示的跟NLLB要求的稍微有点区别）
LANG_MAP = {
    "zh": "zho_Hans",  # 中文简体
    "en": "eng_Latn",  # 英文
    "ja": "jpn_Jpan",  # 日文
    "ko": "kor_Hang",  # 韩文
    "fr": "fra_Latn",  # 法文
    "de": "deu_Latn",  # 德文
    "es": "spa_Latn",  # 西班牙文
    "ru": "rus_Cyrl",  # 俄文
    "ar": "arb_Arab",  # # 阿拉伯文
    # 需要更多语言直接在这里加就行
}


def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    if not text.strip():
        return ""

    tokenizer, model = get_nllb_model()

    src_code = LANG_MAP.get(source_lang, "eng_Latn")
    tgt_code = LANG_MAP.get(target_lang, "zho_Hans")

    tokenizer.src_lang = src_code
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)

    if torch.cuda.is_available():
        inputs = inputs.to("cuda")

    translated_tokens = model.generate(
        **inputs,
        forced_bos_token_id=tokenizer.convert_tokens_to_ids(tgt_code),
        max_length=512,
        num_beams=5,
        early_stopping=True
    )
    return tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0]


# 提取文件文本
def extract_text(file_content: bytes, filename: str) -> str:
    if filename.lower().endswith(".txt"):
        return file_content.decode("utf-8", errors="ignore")
    elif filename.lower().endswith(".docx"):
        doc = docx.Document(io.BytesIO(file_content))
        return "\n".join([p.text for p in doc.paragraphs])
    elif filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file_content))
        return "\n".join([page.extract_text() or "" for page in reader.pages])
    else:
        raise ValueError("只支持 .txt / .docx / .pdf 文件")


# 接口
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/translate/text")
async def translate_text_api(text: str = Form(...), source_lang: str = Form("en"), target_lang: str = Form("zh")):
    result = translate_text(text, source_lang, target_lang)
    return {"translated_text": result}


@app.post("/translate/file")
async def translate_file_api(
    file: UploadFile = File(...),
    source_lang: str = Form("en"),
    target_lang: str = Form("zh")
):
    contents = await file.read()
    try:
        raw_text = extract_text(contents, file.filename)
    except Exception as e:
        return {"error": f"文件读取失败：{str(e)}"}

    # 超长文档分段翻译（每段最多800个字符）
    max_chunk = 800
    chunks = [raw_text[i:i+max_chunk] for i in range(0, len(raw_text), max_chunk)]
    translated_chunks = []

    tokenizer, model = get_nllb_model()
    src_code = LANG_MAP.get(source_lang, "eng_Latn")
    tgt_code = LANG_MAP.get(target_lang, "zho_Hans")
    tokenizer.src_lang = src_code

    for chunk in chunks:
        if not chunk.strip():
            translated_chunks.append("")
            continue
        inputs = tokenizer(chunk, return_tensors="pt", truncation=True, max_length=512)
        if torch.cuda.is_available():
            inputs = inputs.to("cuda")
        with torch.no_grad():
            translated_tokens = model.generate(
                **inputs,
                forced_bos_token_id=tokenizer.convert_tokens_to_ids(tgt_code),
                max_length=512,
                num_beams=5,
                early_stopping=True
            )
        translated_chunks.append(tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0])

    final_result = "\n".join(translated_chunks)

    # 解决中文文件名乱码问题
    import urllib.parse
    safe_filename = urllib.parse.quote(f"translated_{file.filename}")

    return StreamingResponse(
        io.BytesIO(final_result.encode("utf-8")),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename*=utf-8''{safe_filename}"}
    )