import tweepy
from datetime import datetime, timedelta
import os

# ================== CONFIGURA QUI LE TUE CREDENZIALI ==================
consumer_key = "INSERISCI_QUI"
consumer_secret = "INSERISCI_QUI"
access_token = "INSERISCI_QUI"
access_token_secret = "INSERISCI_QUI"

# =====================================================================

# Autenticazione (OAuth 1.0a - necessario per i tuoi dati)
client = tweepy.Client(
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    access_token=access_token,
    access_token_secret=access_token_secret,
    wait_on_rate_limit=True
)

# Ottieni il tuo user ID
me = client.get_me()
user_id = me.data.id
print(f"Account trovato: @{me.data.username} (ID: {user_id})")

# Calcola la settimana scorsa (ultimi 7 giorni)
end_time = datetime.utcnow()
start_time = end_time - timedelta(days=7)

print(f"Recupero post dal {start_time.strftime('%d/%m/%Y')} al {end_time.strftime('%d/%m/%Y')}...")

# Recupera i tuoi post + risposte (senza escludere le replies)
tweets = tweepy.Paginator(
    client.get_users_tweets,
    id=user_id,
    max_results=100,                    # massimo per chiamata
    tweet_fields=["created_at", "public_metrics", "text", "conversation_id", "in_reply_to_user_id"],
    start_time=start_time,
    end_time=end_time,
    exclude=None                        # None = include replies e retweets
).flatten(limit=200)                    # limite alto, con 10 post/settimana è più che sufficiente

# Preparazione del contenuto Markdown
md = f"# Report Settimanale X - @{me.data.username}\n\n"
md += f"**Periodo:** {start_time.strftime('%d %B %Y')} – {end_time.strftime('%d %B %Y')}\n\n"
md += f"**Generato il:** {datetime.now().strftime('%d/%m/%Y alle %H:%M')}\n\n"

posts_list = []
total_impressions = 0
total_likes = 0
total_reposts = 0
total_replies = 0

print("Elaborazione post...")

for tweet in tweets:
    metrics = tweet.public_metrics or {}
    impressions = metrics.get("impression_count", "N/A")
    likes = metrics.get("like_count", 0)
    reposts = metrics.get("retweet_count", 0)
    replies_count = metrics.get("reply_count", 0)
    
    total_impressions += impressions if isinstance(impressions, int) else 0
    total_likes += likes
    total_reposts += reposts
    total_replies += replies_count
    
    # Testo breve (troncato per la tabella)
    text_short = tweet.text.replace("\n", " ")[:120]
    if len(tweet.text) > 120:
        text_short += "..."
    
    is_reply = tweet.in_reply_to_user_id is not None
    
    posts_list.append({
        "date": tweet.created_at.strftime("%d/%m %H:%M") if tweet.created_at else "N/A",
        "is_reply": "✅ Risposta" if is_reply else "Post originale",
        "text": text_short,
        "impressions": impressions,
        "likes": likes,
        "reposts": reposts,
        "replies": replies_count,
        "url": f"https://x.com/{me.data.username}/status/{tweet.id}"
    })

# Riepilogo
md += "## 📊 Riepilogo Settimanale\n\n"
md += f"- **Post totali (inclusi risposte):** {len(posts_list)}\n"
md += f"- **Impressions totali:** {total_impressions:,}\n"
md += f"- **Likes totali:** {total_likes:,}\n"
md += f"- **Repost totali:** {total_reposts:,}\n"
md += f"- **Risposte ricevute:** {total_replies:,}\n\n"

# Tabella tutti i post
md += "## 📋 Tutti i post e risposte\n\n"
md += "| Data | Tipo | Testo | Impressions | Likes | Reposts | Replies | Link |\n"
md += "|------|------|-------|-------------|-------|---------|---------|------|\n"

for p in sorted(posts_list, key=lambda x: x["date"], reverse=True):
    md += f"| {p['date']} | {p['is_reply']} | {p['text'].replace('|', '\\|')} | {p['impressions']} | {p['likes']} | {p['reposts']} | {p['replies']} | [Vai al post]({p['url']}) |\n"

# Top 3 post (per impressions)
md += "\n## 🏆 Top 3 Post della Settimana (per impressions)\n\n"
top3 = sorted(posts_list, key=lambda x: x["impressions"] if isinstance(x["impressions"], int) else 0, reverse=True)[:3]

for i, p in enumerate(top3, 1):
    md += f"**{i}.** {p['text'][:100]}...\n"
    md += f"   - Impressions: **{p['impressions']}** | Likes: {p['likes']} | Reposts: {p['reposts']}\n\n"

md += "\n---\n\n*Report generato automaticamente con script Python + X API v2*"

# Salva il file
filename = f"report_x_settimanale_{datetime.now().strftime('%Y-%m-%d')}.md"
with open(filename, "w", encoding="utf-8") as f:
    f.write(md)

print(f"\n✅ Report creato con successo!")
print(f"   File: {filename}")
print(f"   Post recuperati: {len(posts_list)}")