FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
```eof

بعد از اینکه این کار رو کردی، برگرد توی سایت Render و روی دکمه **`Manual Deploy -> Deploy latest commit`** بزن تا رباتت بدون هیچ خطایی درجا روشن بشه!
