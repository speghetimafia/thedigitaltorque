#!/usr/bin/env python3
"""
Instagram Media Extractor using Playwright
This script uses browser automation to extract media from an Instagram profile.
It saves images and videos locally and generates a JSON feed for the frontend.
"""

import asyncio
import json
import os
import re
import hashlib
from datetime import datetime

# Check if playwright is installed
try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Installing playwright...")
    import subprocess
    subprocess.run(["python3", "-m", "pip", "install", "playwright"], check=True)
    subprocess.run(["python3", "-m", "playwright", "install", "chromium"], check=True)
    from playwright.async_api import async_playwright

try:
    import requests
except ImportError:
    import subprocess
    subprocess.run(["python3", "-m", "pip", "install", "requests"], check=True)
    import requests

# Configuration
TARGET_PROFILE = "thedigitaltorque"
OUTPUT_DIR = "public/assets/instagram"
JSON_OUTPUT = "public/instagram-feed.json"
MAX_POSTS = 12
INSTAGRAM_URL = f"https://www.instagram.com/{TARGET_PROFILE}/"


def setup_directories():
    """Create output directories if they don't exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def download_media(url, filepath):
    """Download media file from URL to local path."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Referer': 'https://www.instagram.com/',
        }
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"  ✓ Downloaded: {os.path.basename(filepath)}")
            return True
        else:
            print(f"  ✗ Failed to download (status {response.status_code})")
    except Exception as e:
        print(f"  ✗ Download error: {e}")
    return False


async def download_blob(page, url, filepath):
    """Download blob/local resource using browser context."""
    try:
        # Fetch blob data as binary in the browser context
        # We convert to Array because return value must be serializable
        data = await page.evaluate(r"""async (url) => {
            const response = await fetch(url);
            const buffer = await response.arrayBuffer();
            return Array.from(new Uint8Array(buffer));
        }""", url)
        
        with open(filepath, 'wb') as f:
            f.write(bytes(data))
        print(f"  ✓ Downloaded blob: {os.path.basename(filepath)}")
        return True
    except Exception as e:
        print(f"  ✗ Blob download error: {e}")
        return False


def get_file_hash(url):
    """Generate a short hash from URL for consistent filenames."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


async def extract_instagram_posts():
    """Main extraction function using Playwright."""
    setup_directories()
    posts_data = []
    
    print(f"\n{'='*60}")
    print(f"Instagram Feed Extractor")
    print(f"Target: @{TARGET_PROFILE}")
    print(f"{'='*60}\n")
    
    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        print(f"Navigating to {INSTAGRAM_URL}...")
        
        try:
            await page.goto(INSTAGRAM_URL, wait_until='networkidle', timeout=30000)
        except Exception as e:
            print(f"Initial load timeout, continuing anyway... ({e})")
        
        # Wait for content to load
        await asyncio.sleep(3)
        
        # Check if we're blocked or need login
        page_content = await page.content()
        if "Login" in page_content and "Log in" in page_content:
            print("\n⚠️  Instagram is requesting login. Trying to proceed...")
        
        # Try to find post links
        print("Scanning for posts...")
        
        # Instagram profile posts are in <article> or links matching /p/ or /reel/
        post_links = await page.query_selector_all('a[href*="/p/"], a[href*="/reel/"]')
        
        seen_posts = set()
        post_urls = []
        
        for link in post_links:
            href = await link.get_attribute('href')
            if href and href not in seen_posts:
                seen_posts.add(href)
                if href.startswith('/'):
                    href = f"https://www.instagram.com{href}"
                post_urls.append(href)
        
        print(f"Found {len(post_urls)} unique posts")
        
        # Process each post
        for idx, post_url in enumerate(post_urls[:MAX_POSTS]):
            print(f"\n[{idx+1}/{min(len(post_urls), MAX_POSTS)}] Processing: {post_url}")
            
            try:
                await page.goto(post_url, wait_until='domcontentloaded', timeout=20000)
                await asyncio.sleep(2)
                
                # Determine post type
                is_reel = '/reel/' in post_url
                post_type = 'reel' if is_reel else 'image'
                
                # Extract shortcode from URL
                match = re.search(r'/(p|reel)/([A-Za-z0-9_-]+)', post_url)
                shortcode = match.group(2) if match else f"post_{idx}"
                
                # Check for login wall again on post page
                if "Login" in await page.title():
                    print("  ⚠️  Hit login wall on post page")
                    continue
                
                post_info = {
                    "id": shortcode,
                    "permalink": post_url,
                    "type": post_type,
                    "media_type": "VIDEO" if is_reel else "IMAGE",
                    "caption": "",
                    "timestamp": datetime.utcnow().isoformat(),
                    "thumbnail_url": "",
                    "media_url": "",
                    "video_url": ""
                }
                
                # Try to get image/video from the page
                if is_reel:
                    # For reels, look for video element
                    video = await page.query_selector('video')
                    if video:
                        video_src = await video.get_attribute('src')
                        poster = await video.get_attribute('poster')
                        
                        if video_src:
                            vid_filename = f"{shortcode}.mp4"
                            vid_path = os.path.join(OUTPUT_DIR, vid_filename)
                            
                            success = False
                            if video_src.startswith('blob:'):
                                success = await download_blob(page, video_src, vid_path)
                            else:
                                success = download_media(video_src, vid_path)
                                
                            if success:
                                post_info["video_url"] = f"/assets/instagram/{vid_filename}"
                        
                        if poster:
                            img_filename = f"{shortcode}.jpg"
                            img_path = os.path.join(OUTPUT_DIR, img_filename)
                            if download_media(poster, img_path):
                                post_info["thumbnail_url"] = f"/assets/instagram/{img_filename}"
                                post_info["media_url"] = post_info["thumbnail_url"]
                else:
                    # For images, look for img elements
                    # Relaxed selector: look for the largest image in the main role or article
                    images = await page.query_selector_all('main img, article img')
                    for img in images:
                        src = await img.get_attribute('src')
                        if src and 'scontent' in src:
                            img_filename = f"{shortcode}.jpg"
                            img_path = os.path.join(OUTPUT_DIR, img_filename)
                            if download_media(src, img_path):
                                post_info["media_url"] = f"/assets/instagram/{img_filename}"
                                post_info["thumbnail_url"] = post_info["media_url"]
                            break
                
                # Only add if we got some media
                if post_info["media_url"] or post_info["video_url"]:
                    posts_data.append(post_info)
                    print(f"  ✓ Added post: {shortcode}")
                else:
                    print(f"  ✗ No media found for this post")
                    
            except Exception as e:
                print(f"  ✗ Error processing post: {e}")
                continue
        
        await browser.close()
    
    # Write JSON feed
    if posts_data:
        with open(JSON_OUTPUT, 'w') as f:
            json.dump(posts_data, f, indent=4)
        print(f"\n{'='*60}")
        print(f"✓ SUCCESS: Generated feed with {len(posts_data)} posts")
        print(f"  Feed: {JSON_OUTPUT}")
        print(f"  Media: {OUTPUT_DIR}/")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'='*60}")
        print("✗ FAILED: No posts could be extracted")
        print("  This may be due to Instagram rate limiting or login requirements.")
        print("  Try again later or use manual extraction.")
        print(f"{'='*60}\n")
    
    return posts_data


def main():
    """Entry point."""
    asyncio.run(extract_instagram_posts())


if __name__ == "__main__":
    main()
