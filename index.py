import streamlit as st
import yt_dlp
import moviepy.editor as mp
import whisper
from moviepy.editor import *
import numpy as np
import os
import tempfile
from pathlib import Path
import cv2
from PIL import Image
import speech_recognition as sr
from gtts import gTTS
import io
import re

st.set_page_config(page_title="YouTube Shorts Maker", layout="wide")

class YouTubeShortsMaker:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def download_video(self, url, output_path):
        """YouTube video download karega"""
        ydl_opts = {
            'format': 'best[height<=1080]',
            'outtmpl': output_path,
            'merge_output_format': 'mp4'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return output_path
    
    def get_video_duration(self, video_path):
        """Video duration nikalega"""
        clip = VideoFileClip(video_path)
        duration = clip.duration
        clip.close()
        return duration
    
    def extract_audio(self, video_path, audio_path):
        """Audio extract karega"""
        video = VideoFileClip(video_path)
        audio = video.audio
        audio.write_audiofile(audio_path, verbose=False, logger=None)
        video.close()
        audio.close()
    
    def generate_subtitles(self, audio_path):
        """Whisper se subtitles generate karega"""
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        return result['segments']
    
    def create_subtitle_clips(self, segments, video_path):
        """Subtitle clips banayega"""
        video = VideoFileClip(video_path)
        clips = []
        
        for segment in segments:
            start_time = segment['start']
            end_time = segment['end']
            text = segment['text'].strip()
            
            if end_time - start_time > 2:  # Minimum 2 sec clips
                subclip = video.subclip(start_time, end_time)
                
                # Subtitle text overlay
                txt_clip = TextClip(
                    text, 
                    fontsize=50, 
                    color='white',
                    stroke_color='black',
                    stroke_width=2,
                    font='Arial-Bold'
                ).set_position(('center', 'bottom')).set_duration(end_time - start_time)
                
                final_clip = CompositeVideoClip([subclip, txt_clip])
                clips.append(final_clip)
        
        video.close()
        return clips
    
    def detect_scene_changes(self, video_path):
        """Scene changes detect karega"""
        cap = cv2.VideoCapture(video_path)
        prev_frame = None
        scenes = []
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
            
            if prev_frame is not None:
                frame_diff = cv2.absdiff(prev_frame, gray)
                thresh = cv2.threshold(frame_diff, 30, 255, cv2.THRESH_BINARY)[1]
                change_ratio = np.mean(thresh) / 255.0
                
                if change_ratio > 0.15:  # Scene change threshold
                    scenes.append(frame_count / cap.get(cv2.CAP_PROP_FPS))
            
            prev_frame = gray
            frame_count += 1
        
        cap.release()
        return scenes
    
    def create_shorts(self, video_path, subtitle_clips):
        """Multiple shorts banayega"""
        duration = self.get_video_duration(video_path)
        scene_changes = self.detect_scene_changes(video_path)
        
        # 15-60 sec ke shorts banayenge
        shorts = []
        max_shorts = min(10, len(subtitle_clips))  # Max 10 shorts
        
        for i in range(max_shorts):
            start_time = max(0, i * 15)  # 15 sec intervals
            end_time = min(duration, start_time + 45)  # Max 45 sec
            
            # Best matching subtitle clip
            best_clip = None
            best_score = 0
            
            for clip in subtitle_clips:
                clip_start = getattr(clip, 'start', 0)
                clip_end = getattr(clip, 'end', duration)
                
                overlap = min(end_time, clip_end) - max(start_time, clip_start)
                if overlap > best_score:
                    best_score = overlap
                    best_clip = clip
            
            if best_clip:
                shorts.append(best_clip)
        
        return shorts
    
    def enhance_short(self, clip):
        """Basic editing: speed, zoom, effects"""
        # Random zoom effect
        zoom_factor = 1.05 + np.random.random() * 0.1
        
        # Speed variation
        speed_factor = 1.0 + np.random.random() * 0.2
        
        enhanced = clip.fx(afx.resize, lambda t: zoom_factor)
        enhanced = enhanced.fx(afx.speedx, speed_factor)
        
        # Add intro/outro text
        intro_text = TextClip("🔥 TRENDING SHORTS 🔥", 
                            fontsize=60, color='yellow', font='Arial-Bold'
                           ).set_duration(2).set_position('center')
        
        outro_text = TextClip("👉 Follow for more! 👈", 
                            fontsize=50, color='white', font='Arial-Bold',
                            stroke_color='black', stroke_width=2
                           ).set_duration(2).set_position('center')
        
        final_clip = concatenate_videoclips([
            intro_text.set_start(0),
            enhanced,
            outro_text.set_start(clip.duration - 2)
        ])
        
        return final_clip.set_duration(60)  # Max 60 sec
    
    def export_short(self, clip, output_path):
        """HD quality mein export karega"""
        clip_resized = clip.resize(height=1080)
        clip_resized.write_videofile(
            output_path,
            fps=30,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            verbose=False,
            logger=None
        )

def main():
    st.title("🎥 YouTube Shorts Maker Pro")
    st.markdown("---")
    
    maker = YouTubeShortsMaker()
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("📥 Input")
        youtube_url = st.text_input("YouTube Video Link", placeholder="https://youtube.com/watch?v=...")
        
        if st.button("🚀 Generate Shorts", type="primary"):
            if youtube_url:
                with st.spinner("Downloading video..."):
                    try:
                        # Download video
                        video_path = os.path.join(maker.temp_dir, "input_video.mp4")
                        maker.download_video(youtube_url, video_path)
                        
                        st.success("✅ Video downloaded!")
                        
                        # Extract audio & generate subtitles
                        with st.spinner("Generating subtitles..."):
                            audio_path = os.path.join(maker.temp_dir, "audio.wav")
                            maker.extract_audio(video_path, audio_path)
                            segments = maker.generate_subtitles(audio_path)
                        
                        # Create subtitle clips
                        with st.spinner("Creating shorts..."):
                            subtitle_clips = maker.create_subtitle_clips(segments, video_path)
                            shorts = maker.create_shorts(video_path, subtitle_clips)
                        
                        # Export shorts
                        st.success(f"✅ {len(shorts)} Shorts ready!")
                        
                        # Display shorts
                        for i, short in enumerate(shorts):
                            enhanced_short = maker.enhance_short(short)
                            output_path = os.path.join(maker.temp_dir, f"short_{i+1}.mp4")
                            maker.export_short(enhanced_short, output_path)
                            
                            st.video(output_path)
                            st.download_button(
                                label=f"📥 Download Short {i+1}",
                                data=open(output_path, 'rb').read(),
                                file_name=f"short_{i+1}.mp4",
                                mime="video/mp4"
                            )
                            
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            else:
                st.warning("Please enter YouTube URL")
    
    with col2:
        st.subheader("✨ Features")
        st.markdown("""
        - **HD Quality (1080p)**
        - **Auto Subtitles**
        - **Scene Detection**
        - **Multiple Shorts**
        - **Zoom Effects**
        - **Trending Text**
        - **Ready-to-post**
        """)
        
        st.subheader("📊 Stats")
        if 'segments' in locals():
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Total Clips", len(locals().get('subtitle_clips', [])))
            with col_b:
                st.metric("Shorts Generated", len(locals().get('shorts', [])))

if __name__ == "__main__":
    main()
