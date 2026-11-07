import discord
from discord.ext import commands
import google.generativeai as genai
import os
import requests
import io
from PyPDF2 import PdfReader
import docx
from flask import Flask
from threading import Thread

# 1. SETUP SERVER RENDER AGAR ONLINE 24 JAM
app = Flask(__name__)
@app.route('/')
def home():
    return "Server Bot Berjalan 24 Jam!"
def run():
    app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. SETUP BOT & GEMINI API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Variabel lokal untuk menyimpan limit gambar user
limit_gambar = {}
LIMIT_MAKSIMAL = 5

@bot.event
async def on_ready():
    print(f"Login berhasil sebagai {bot.user}")

# 3. FITUR: TANYA TUGAS & BACA DOKUMEN (PDF/DOCX)
@bot.command()
async def tanya(ctx, *, pertanyaan="Tolong rangkum/jelaskan dokumen ini"):
    async with ctx.typing():
        teks_dokumen = ""
        
        # Cek apakah user melampirkan file
        if ctx.message.attachments:
            for file in ctx.message.attachments:
                try:
                    file_bytes = await file.read()
                    if file.filename.endswith('.pdf'):
                        reader = PdfReader(io.BytesIO(file_bytes))
                        for page in reader.pages:
                            teks_dokumen += page.extract_text() + "\n"
                    elif file.filename.endswith('.docx'):
                        doc = docx.Document(io.BytesIO(file_bytes))
                        for para in doc.paragraphs:
                            teks_dokumen += para.text + "\n"
                    else:
                        await ctx.send("Format tidak didukung. Kirim PDF atau DOCX saja.")
                        return
                except Exception as e:
                    await ctx.send(f"Gagal membaca file: {e}")
                    return

        # Susun prompt dengan persona asisten Sistem Informasi
        prompt = "Kamu adalah AI asisten untuk mahasiswa program studi Sistem Informasi. Jawablah dengan terstruktur, logis, dan berikan pendekatan analitis jika relevan.\n"
        if teks_dokumen:
            # Membatasi teks dokumen agar tidak melewati batas token Gemini
            prompt += f"\nKonteks Dokumen:\n{teks_dokumen[:15000]}\n"
        prompt += f"\nPertanyaan User: {pertanyaan}"

        try:
            response = model.generate_content(prompt)
            jawaban = response.text
            
            # Pecah pesan jika lebih dari 2000 karakter (limit Discord)
            for chunk in [jawaban[i:i+2000] for i in range(0, len(jawaban), 2000)]:
                await ctx.send(chunk)
        except Exception as e:
            await ctx.send(f"Terjadi kesalahan pada AI: {e}")

# 4. FITUR: BUAT GAMBAR BERDASARKAN LIMIT
@bot.command()
async def gambar(ctx, *, deskripsi):
    user_id = ctx.author.id
    
    # Cek dan berikan limit jika user belum pernah generate
    if user_id not in limit_gambar:
        limit_gambar[user_id] = LIMIT_MAKSIMAL
        
    if limit_gambar[user_id] <= 0:
        await ctx.send("Maaf, limit pembuatan gambar kamu sudah habis untuk sesi ini!")
        return
        
    async with ctx.typing():
        # Generate gambar gratis via Pollinations API
        url = f"https://image.pollinations.ai/prompt/{deskripsi}?width=1024&height=1024&nologo=1"
        try:
            res = requests.get(url)
            if res.status_code == 200:
                limit_gambar[user_id] -= 1
                sisa = limit_gambar[user_id]
                
                file_gambar = discord.File(io.BytesIO(res.content), filename="hasil.png")
                await ctx.send(f"🎨 Sisa limit kamu: **{sisa}/{LIMIT_MAKSIMAL}**", file=file_gambar)
            else:
                await ctx.send("Gagal membuat gambar, coba deskripsi lain.")
        except Exception as e:
            await ctx.send(f"Error: {e}")

# Jalankan background web server dan jalankan bot
keep_alive()
bot.run(os.environ.get("DISCORD_TOKEN"))