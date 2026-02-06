#!/usr/bin/env python3
"""
Instagram Extractor V2 using Instaloader.
This bypasses some of the scraping issues by using the instaloader library.
"""

import instaloader
import json
import os
import requests
import time

# Config
TARGET_PROFILE = "thedigitaltorque"
OUTPUT_DIR = "public/assets/instagram"
JSON_OUTPUT = "public/instagram-feed.json"
MAX_POSTS = 12

def extract_v2():
    print(f"Starting extraction for {TARGET_PROFILE} using Instaloader...")
    
    L = instaloader.Instaloader()
    
    # Try to keep session anonymous
    
    try:
        profile = instaloader.Profile.from_username(L.context, TARGET_PROFILE)
    except Exception as e:
        print(f"Error accessing profile: {e}")
        # Sometimes it fails if not logged in.
        return

    # Ensure output dir exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    posts_data = []
    
    count = 0
    # get_posts is a generator
    posts = profile.get_posts()
    
    try:
        for post in posts:
            if count >= MAX_POSTS:
                break
                
            print(f"Processing post {post.shortcode}...")
            
            # Determine type
            is_video = post.is_video
            post_type = "reel" if is_video else "image"
            
            # Paths
            base_name = post.shortcode
            
            thumbnail_url = ""
            video_url = ""
            
            try:
                # Download Image (Thumbnail or Main Image)
                img_filename = f"{base_name}.jpg"
                img_path = os.path.join(OUTPUT_DIR, img_filename)
                
                # Use requests to download to avoid instaloader specific naming/metadata files
                response = requests.get(post.url)
                if response.status_code == 200:
                    with open(img_path, 'wb') as f:
                        f.write(response.content)
                    thumbnail_url = f"/assets/instagram/{img_filename}"
                else:
                    print(f"  Failed to download image: {response.status_code}")
                
                # Download Video if Reel
                if is_video and post.video_url:
                    vid_filename = f"{base_name}.mp4"
                    vid_path = os.path.join(OUTPUT_DIR, vid_filename)
                    
                    response = requests.get(post.video_url)
                    if response.status_code == 200:
                        with open(vid_path, 'wb') as f:
                            f.write(response.content)
                        video_url = f"/assets/instagram/{vid_filename}"
                    else:
                        print(f"  Failed to download video: {response.status_code}")

                # Add to data if we have at least a thumbnail
                if thumbnail_url:
                    posts_data.append({
                        "id": post.shortcode,
                        "permalink": f"https://www.instagram.com/p/{post.shortcode}/",
                        "type": post_type,
                        "thumbnail_url": thumbnail_url,
                        "video_url": video_url,
                        "caption": post.caption if post.caption else ""
                    })
                    print(f"  ✓ Added {post_type}")
                    count += 1
                
                # Polite delay
                time.sleep(2)
                
            except Exception as e:
                print(f"Failed to process post {post.shortcode}: {e}")
                
    except Exception as e:
        print(f"Error during iteration: {e}")

    # Write JSON
    if posts_data:
        with open(JSON_OUTPUT, 'w') as f:
            json.dump(posts_data, f, indent=4)
        print(f"Done. Extracted {len(posts_data)} posts to {JSON_OUTPUT}.")
    else:
        print("No posts extracted.")

if __name__ == "__main__":
    extract_v2()
