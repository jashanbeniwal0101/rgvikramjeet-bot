# main.py
import os
import json
import aiohttp
import asyncio
from base64 import b64decode
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from pyrogram import Client, filters
from pyrogram.types import Message

from config import API_ID, API_HASH, BOT_TOKEN, API_BASE, API_KEY, DEFAULT_HEADERS

app = Client("rgvikramjeet_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# All your logic here as before...
def decrypt(encrypted_data: str) -> str:
    """Decrypt RG Vikramjeet links using AES-CBC"""
    try:
        # Extract Base64 encoded ciphertext
        enc = b64decode(encrypted_data.split(':')[0])
        key = b'638udh3829162018'
        iv = b'fedcba9876543210'
        
        # Decrypt and unpad
        cipher = AES.new(key, AES.MODE_CBC, iv)
        plaintext = unpad(cipher.decrypt(enc), AES.block_size)
        return plaintext.decode('utf-8')
    except Exception as e:
        print(f"Decryption failed: {e}")
        return ""

async def fetch_json(session: aiohttp.ClientSession, url: str, headers: dict) -> dict:
    """Fetch JSON data from API with error handling"""
    try:
        async with session.get(url, headers=headers) as response:
            return await response.json()
    except Exception as e:
        print(f"API request failed: {e}")
        return {}

async def process_course_content(session: aiohttp.ClientSession, course_id: str, headers: dict, filename: str):
    """Extract all content from a course and save to file"""
    with open(filename, "w", encoding="utf-8") as f:
        # Fetch subjects
        subjects_url = f"{API_BASE}/get/allsubjectfrmlivecourseclass?courseid={course_id}"
        subjects_res = await fetch_json(session, subjects_url, headers)
        
        if not subjects_res.get("data"):
            f.write("No subjects found for this course\n")
            return
        
        for subject in subjects_res["data"]:
            subject_id = subject.get("subjectid")
            subject_name = subject.get("subject_name", "Unknown Subject")
            f.write(f"\n\n===== {subject_name} =====\n\n")
            
            # Fetch topics
            topics_url = f"{API_BASE}/get/alltopicfrmlivecourseclass?courseid={course_id}&subjectid={subject_id}"
            topics_res = await fetch_json(session, topics_url, headers)
            
            if not topics_res.get("data"):
                continue
            
            for topic in topics_res["data"]:
                topic_id = topic.get("topicid")
                topic_name = topic.get("topic_name", "Unknown Topic")
                f.write(f"\n--- {topic_name} ---\n")
                
                # Fetch content items
                content_url = (
                    f"{API_BASE}/get/livecourseclassbycoursesubtopconceptapiv3?"
                    f"topicid={topic_id}&courseid={course_id}&subjectid={subject_id}"
                )
                content_res = await fetch_json(session, content_url, headers)
                
                if not content_res.get("data"):
                    continue
                
                # Process content
                for item in content_res["data"]:
                    title = item.get("Title", "Untitled")
                    
                    # Handle video content
                    if dl_link := item.get("download_link"):
                        decrypted = decrypt(dl_link)
                        if decrypted:
                            f.write(f"{title}: {decrypted}\n")
                    
                    # Handle PDF content
                    for pdf_field in ["pdf_link", "pdf_link2"]:
                        if pdf_link := item.get(pdf_field):
                            decrypted = decrypt(pdf_link)
                            if decrypted:
                                f.write(f"{title} [PDF]: {decrypted}\n")
                    
                    # Handle encrypted video links
                    for enc_link in item.get("encrypted_links", []):
                        path = enc_link.get("path")
                        key = enc_link.get("key")
                        if path and key:
                            dec_path = decrypt(path)
                            dec_key = decrypt(key)
                            if dec_path and dec_key:
                                f.write(f"{title}: {dec_path}*{dec_key}\n")

@app.on_message(filters.command(["rgvikramjeet"]) & ~filters.edited)
async def handle_command(client: Client, message: Message):
    """Main command handler for batch extraction"""
    # Step 1: Get credentials
    cred_msg = await message.reply("🔑 Send your ID and password in this format:\n\n`ID*PASSWORD`")
    cred_response = await client.listen(message.chat.id)
    credentials = cred_response.text
    await cred_response.delete()
    await cred_msg.delete()
    
    # Step 2: Authenticate
    if '*' not in credentials:
        return await message.reply("❌ Invalid format! Use `ID*PASSWORD`")
    
    email, password = credentials.split('*', 1)
    login_data = {"email": email, "password": password}
    token = None
    user_id = None
    
    async with aiohttp.ClientSession() as session:
        # Login request
        try:
            async with session.post(
                f"{API_BASE}/post/userLogin",
                data=login_data,
                headers=HEADERS
            ) as response:
                login_res = await response.json()
                
            if not login_res.get("status"):
                return await message.reply(f"❌ Login failed: {login_res.get('message', 'Unknown error')}")
            
            user_id = login_res["data"]["userid"]
            token = login_res["data"]["token"]
            await message.reply("✅ Login successful! Fetching your courses...")
        except Exception as e:
            return await message.reply(f"🚫 Connection error: {str(e)}")
        
        # Step 3: Fetch courses
        auth_headers = {
            "Client-Service": "Appx",
            "Auth-Key": API_KEY,
            "Authorization": token,
            "User-ID": user_id
        }
        
        courses = []
        endpoints = [
            f"{API_BASE}/get/get_all_purchases?userid={user_id}&item_type=10",
            f"{API_BASE}/get/mycourseweb?userid={user_id}"
        ]
        
        for url in endpoints:
            course_res = await fetch_json(session, url, auth_headers)
            if course_data := course_res.get("data"):
                # Handle different response formats
                if isinstance(course_data, list) and course_data:
                    if "coursedt" in course_data[0]:
                        for item in course_data:
                            for course in item.get("coursedt", []):
                                courses.append((course["id"], course["course_name"]))
                    else:
                        for course in course_data:
                            courses.append((course["id"], course["course_name"]))
                break
        
        if not courses:
            return await message.reply("❌ No courses found for your account")
        
        # Step 4: Course selection
        courses_list = "\n".join([f"`{c[0]}` - {c[1]}" for c in courses])
        batch_msg = await message.reply(
            f"📚 Available Courses:\n\n{courses_list}\n\n"
            "**Reply with Course ID to download**"
        )
        
        course_msg = await client.listen(message.chat.id)
        course_id = course_msg.text.strip()
        await course_msg.delete()
        await batch_msg.delete()
        
        # Validate course ID
        if not any(c[0] == course_id for c in courses):
            return await message.reply("❌ Invalid Course ID")
        
        # Get course name for filename
        course_name = next((c[1] for c in courses if c[0] == course_id), "Unknown")
        safe_name = "".join(c if c.isalnum() else "_" for c in course_name)
        filename = f"{safe_name}_{course_id}.txt"
        
        # Step 5: Content extraction
        status_msg = await message.reply("⏳ Extracting content... This may take 2-5 minutes")
        await process_course_content(session, course_id, auth_headers, filename)
        await status_msg.delete()
        
        # Step 6: Send results
        await message.reply_document(
            filename,
            caption=f"📁 {course_name} - Extracted Content"
        )
        
        # Cleanup
        os.remove(filename)

if __name__ == "__main__":
    print("RG Vikramjeet Batch Extractor Bot Started!")
    app.run()
