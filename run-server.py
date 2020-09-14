import os
from flask import Flask, render_template, request
import torch
import random
import numpy as np
from utils import header, add_content, box
from wtforms import Form, TextField, validators, SubmitField
import torch
import torch.nn.functional as F
import os
import argparse
from tqdm import trange
from transformers import GPT2LMHeadModel
import generate

# copied from generate.py
parser = argparse.ArgumentParser()
parser.add_argument('--device', default='0,1,2,3', type=str, required=False, help='生成设备')
parser.add_argument('--length', default=-1, type=int, required=False, help='生成长度')
parser.add_argument('--batch_size', default=1, type=int, required=False, help='生成的batch size')
parser.add_argument('--nsamples', default=1
                    , type=int, required=False, help='生成几个样本')
parser.add_argument('--temperature', default=2, type=float, required=False, help='文章生成的隨機度ˇ')
parser.add_argument('--topk', default=12, type=int, required=False, help='最高几选一')
parser.add_argument('--topp', default=3, type=float, required=False, help='最高积累概率')
parser.add_argument('--model_config', default='config/model_config_small.json', type=str, required=False,
                    help='模型参数')
parser.add_argument('--tokenizer_path', default='cache/vocab_processed.txt', type=str, required=False, help='词表路径')
parser.add_argument('--model_path', default='model/final_model', type=str, required=False, help='模型路径')
parser.add_argument('--prefix', default='豬肉', type=str, required=False, help='生成文章的开头')
parser.add_argument('--no_wordpiece', action='store_true', help='不做word piece切词')
parser.add_argument('--segment', action='store_true', help='中文以词为单位')
parser.add_argument('--fast_pattern', action='store_true', help='采用更加快的方式生成文本')
parser.add_argument('--save_samples', action='store_true', help='保存产生的样本')
parser.add_argument('--save_samples_path', default='generate_sample/', type=str, required=False, help="保存样本的路径")
parser.add_argument('--repetition_penalty', default=1.0, type=float, required=False)

args = parser.parse_args()
print('args:\n' + args.__repr__())

if args.segment:
    from tokenizations import tokenization_bert_word_level as tokenization_bert
else:
    from tokenizations import tokenization_bert

os.environ["CUDA_VISIBLE_DEVICES"] = args.device  # 此处设置程序使用哪些显卡
length = args.length
batch_size = args.batch_size
nsamples = args.nsamples
temperature = args.temperature
topk = args.topk
topp = args.topp
repetition_penalty = args.repetition_penalty

device = "cuda" if torch.cuda.is_available() else "cpu"

tokenizer = tokenization_bert.BertTokenizer(vocab_file=args.tokenizer_path)
model = GPT2LMHeadModel.from_pretrained(args.model_path)
model.to(device)
model.eval()

n_ctx = model.config.n_ctx
if length == -1:
    length = model.config.n_ctx

def text_generator(seed):
    generated_texts = []

    # generate text
    raw_text = seed
    context_tokens = tokenizer.convert_tokens_to_ids(tokenizer.tokenize(raw_text))
    generated = 0
    for _ in range(nsamples // batch_size):
        out = generate.generate(
            n_ctx=n_ctx,
            model=model,
            context=context_tokens,
            length=length,
            is_fast_pattern=args.fast_pattern, tokenizer=tokenizer,
            temperature=temperature, top_k=topk, top_p=topp, repitition_penalty=repetition_penalty, device=device
        )
        for i in range(batch_size):
            generated += 1
            text = tokenizer.convert_ids_to_tokens(out)
            for i, item in enumerate(text[:-1]):  # 确保英文前后有空格
                if generate.is_word(item) and generate.is_word(text[i + 1]):
                    text[i] = item + ' '
            for i, item in enumerate(text):
                if item == '[MASK]':
                    text[i] = ''
                elif item == '[CLS]':
                    text[i] = '\n\n'
                elif item == '[SEP]':
                    text[i] = '\n'
            info = "=" * 40 + " SAMPLE " + str(generated) + " " + "=" * 40 + "\n"
            print(info)
            text = ''.join(text).replace('##', '').strip()
            print(text)

            generated_texts.append(text)
    print("=" * 80)
    if generated == nsamples:
        return generated_texts


# Create app
app = Flask(__name__)


class ReusableForm(Form):
    """User entry form for entering specifics for generation"""
    # Starting seed
    seed = TextField("Enter a seed sentence:", validators=[
                     validators.InputRequired()])

    # Submit button
    submit = SubmitField("Enter")

# Home page
@app.route("/", methods=['GET', 'POST'])
def home():
    """Home page of app with form"""
    # Create form
    form = ReusableForm(request.form)

    # On form entry and all conditions met
    if request.method == 'POST' and form.validate():
        # Extract information
        seed = request.form['seed']
        # Generate a random sequence
        return render_template('seeded.html', seed=seed, input=text_generator(seed=seed)[0])
    # Send template information to index.html
    return render_template('index.html', form=form)


if __name__ == "__main__":
    print(("* Loading model and Flask starting server..."
           "please wait until server has fully started"))
 
    # Run app
    app.run(host="0.0.0.0", port=5000)

    # print(text_generator('豬肉')[0])