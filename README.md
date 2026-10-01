# PDF Link Downloader

Ek local bot jo PDF table ke **Source URL** column ke links ek ek kar ke download karta hai:

- **Red** rang wali rows skip hoti hain.
- Baaki sab links **Order** ke sequence mein download hote hain.
- Har file ka naam Order, Chapter, Section aur Visual # se banta hai, jaise
  `002_Ch1_Sec1.1_Visual2.jpg`.
- Aap khud folder chunte hain ke files kahan save hon.
- Aakhir mein usi folder mein `download_report.csv` banti hai, jis mein har link ka status hota hai.

Koi bhi PDF chalegi jis ke table mein yeh columns hon: `Order`, `Chapter`, `Section`, `Visual #`, `Source URL`.

## Chalane ka tareeqa (Windows)

1. Python install karein: https://www.python.org/downloads/
   (install karte waqt **"Add python.exe to PATH"** zaroor tick karein)
2. Is project ka folder kholein aur **`start.bat`** par double-click karein.
3. Browser mein `http://127.0.0.1:5000` khud khul jayega. **Chrome ya Edge** istemaal karein.
4. PDF chunein, phir **Folder chunein**, phir **Start** dabayein.

Band karne ke liye kaali window mein `Ctrl+C` dabayein ya use band kar dein.

## Achhi baatein

- **Dobara chalayein to pehle wali files skip hoti hain.** Sirf fail hone wale links dobara try hote hain.
- Jo link file nahi balki **web page** hai (jaise YouTube, Adobe Stock, ya kisi website ka item page),
  us par status "Yeh web page hai, file nahi" aata hai. Woh link aap khud khol kar dekh sakte hain.
- Sirf PDF mein diye gaye links hi download hote hain, koi aur nahi.
- Agar koi website bot ko rok de (HTTP 403), to bot aapka **Chrome ya Edge** khud khol kar
  usi mein link kholta hai aur file save karta hai. Woh browser window bot ki hai, use band na karein.

## Developers ke liye

```bash
pip install -r requirements.txt
python src/downloader/app.py   # server
pytest                         # tests
```

Code:
- `src/downloader/pdf_table.py`: PDF se rows nikalta hai aur red rows pehchanta hai
- `src/downloader/app.py`: local server (PDF parse karna, files download karna)
- `src/downloader/browser_fetch.py`: website roke to asli Chrome/Edge se download
- `src/downloader/static/index.html`: browser wala page (folder chunna, sequence se save karna)
