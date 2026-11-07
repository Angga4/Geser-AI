import os 
import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
import requests
import io
from PyPDF2 import PdfReader
import docx
from flask import Flask
from threading import Thread
import urllib.parse


# 1. PENGATURAN TOKEN & API KEY
TOKEN_DISCORD = os.environ.get("DISCORD_TOKEN")
API_KEY_GEMINI = os.environ.get("GEMINI_API_KEY")

# 2. SETUP SERVER RENDER (MATIKAN SEMENTARA DENGAN # SAAT TES LOKAL)
app = Flask(__name__)
@app.route('/')
def home():
    return "Server Bot Berjalan 24 Jam!"
def run():
    app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# 3. SETUP BOT & GEMINI API
genai.configure(api_key=API_KEY_GEMINI)
model = genai.GenerativeModel('gemini-3.6-flash')

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

 
limit_gambar = {}
LIMIT_MAKSIMAL = 5

@bot.event
async def on_ready():
 
    try:
        synced = await bot.tree.sync()
        print("=======================================")
        print(f"✅ Login berhasil sebagai: {bot.user}")
        print(f"✅ Berhasil mendaftarkan {len(synced)} Slash Commands.")
        print("🤖 Bot siap digunakan di Discord!")
        print("=======================================")
    except Exception as e:
        print(f"Gagal mendaftarkan slash command: {e}")

 
# 4. SLASH COMMAND: /tanya
 
@bot.tree.command(name="tanya", description="Tanya asisten AI seputar tugas kuliah")
@app_commands.describe(
    pertanyaan="Ketik pertanyaan atau perintah untuk AI", 
    dokumen="Lampirkan file PDF atau DOCX (Opsional)"
)
async def tanya(interaction: discord.Interaction, pertanyaan: str, dokumen: discord.Attachment = None):
    
    await interaction.response.defer()
    
    teks_dokumen = ""
    
    if dokumen:
        try:
            file_bytes = await dokumen.read()
            if dokumen.filename.endswith('.pdf'):
                reader = PdfReader(io.BytesIO(file_bytes))
                for page in reader.pages:
                    teks_dokumen += page.extract_text() + "\n"
            elif dokumen.filename.endswith('.docx'):
                doc = docx.Document(io.BytesIO(file_bytes))
                for para in doc.paragraphs:
                    teks_dokumen += para.text + "\n"
            else:
                await interaction.followup.send("❌ Format tidak didukung. Harap lampirkan PDF atau DOCX.")
                return
        except Exception as e:
            await interaction.followup.send(f"❌ Gagal membaca dokumen: {e}")
            return


    prompt = "Kamu adalah AI asisten untuk mahasiswa Sistem Informasi. Jawablah dengan terstruktur, logis, dan analitis.\n"
    if teks_dokumen:
        prompt += f"\nKonteks Dokumen:\n{teks_dokumen[:15000]}\n"
    prompt += f"\nPertanyaan User: {pertanyaan}"

    try:
        response = model.generate_content(prompt)
        jawaban = response.text
        
        chunks = [jawaban[i:i+2000] for i in range(0, len(jawaban), 2000)]
        
        await interaction.followup.send(chunks[0])
        
        for chunk in chunks[1:]:
            await interaction.followup.send(chunk)
            
    except Exception as e:
        await interaction.followup.send(f"❌ Terjadi kesalahan pada AI: {e}")

# 5. SLASH COMMAND: /gambar
@bot.tree.command(name="gambar", description="Buat gambar dengan AI")
@app_commands.describe(deskripsi="Deskripsikan gambar yang ingin kamu buat")
async def gambar(interaction: discord.Interaction, deskripsi: str):
    await interaction.response.defer()
    
    user_id = interaction.user.id
    
    if user_id not in limit_gambar:
        limit_gambar[user_id] = LIMIT_MAKSIMAL
        
    if limit_gambar[user_id] <= 0:
        await interaction.followup.send("⚠️ Maaf, limit pembuatan gambar kamu sudah habis untuk sesi ini!")
        return
        
    deskripsi_aman = urllib.parse.quote(deskripsi)
    url = f"https://image.pollinations.ai/prompt/{deskripsi_aman}?width=1024&height=1024&nologo=1"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    try:
        res = requests.get(url, headers=headers)
        
        if res.status_code == 200:
            limit_gambar[user_id] -= 1
            sisa = limit_gambar[user_id]
            
            file_gambar = discord.File(io.BytesIO(res.content), filename="hasil_ai.png")
            await interaction.followup.send(f"🎨 Sisa limit kamu: **{sisa}/{LIMIT_MAKSIMAL}**", file=file_gambar)
        else:
            await interaction.followup.send(f"❌ Gagal membuat gambar. Server Pollinations membalas dengan kode error: {res.status_code}")
            
    except Exception as e:
        await interaction.followup.send(f"❌ Error sistem saat mengunduh gambar: {e}")

bot.run(TOKEN_DISCORD)