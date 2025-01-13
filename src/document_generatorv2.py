import whisper
from groq import Groq
import os
from dotenv import load_dotenv
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from PIL import Image as PILImage
import json
import datetime
import ast

load_dotenv()

class PDFDocGenerator:
    def __init__(self, api_key, output_dir=""):
        self.whisper_model = whisper.load_model("base")
        self.groq_client = Groq(api_key=api_key)
        self.output_dir = output_dir
        self.setup_styles()
    
    def setup_styles(self):
        self.styles = getSampleStyleSheet()

        self.styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#2c3e50'),
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=self.styles['Heading2'],
            fontSize=18,
            spaceAfter=20,
            textColor=colors.HexColor('#34495e'),
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=12,
            leading=16,
            spaceAfter=12,
        ))
        
        self.styles.add(ParagraphStyle(
            name='ImageCaption',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
            alignment=1,
            textColor=colors.grey,
            spaceAfter=20,
        ))

    def process_audio(self, audio_path):
        print("Transcribing audio...")
        result = self.whisper_model.transcribe(audio_path)
        return result['text']
    
    def analyze_content(self, transcript, screenshots):
        print("Analyzing content...")
        prompt = f"""You are a documentation generator. Your task is to create a strictly formatted JSON output for a product documentation based on a transcript and screenshots.

        Transcript: {transcript}
        Number of screenshots: {len(screenshots)}

        Rules for JSON structure(ALL RULES MUST BE FOLLOWED STRICTLY):
        1. The output must be EXACTLY this structure, no additional fields or sections allowed:
        {{
            "title": "Product Name",
            "sections": [
                {{
                    "heading": "Overview",
                    "content": ["paragraph1", "paragraph2"]
                }},
                {{
                    "heading": "Key Features",
                    "content": ["feature1", "[[SCREENSHOT-1]]", "caption1", "feature2", "[[SCREENSHOT-2]]", "caption2"]
                }},
                {{
                    "heading": "Technical Details",
                    "content": ["detail1", "detail2"]
                }}
            ]
        }}

        2. Content rules:
        - Extract the title of the product from the transcription given
        - Each paragraph, feature, and detail should be filled with descriptive content which sells the product to the audience
        - Each screenshot should have a descriptive caption
        - Break the content into clear sections with headers
        - The content added to the given JSON structure should be human-like
        - Content should be between 3-5 sentences in the overview, and between 10-15 sentences in the key features and technical details

        2. Screenshot placement rules:
        - Screenshots MUST ONLY appear in the Key Features section
        - Use exact format "[[SCREENSHOT-1]]" for first screenshot, "[[SCREENSHOT-2]]" for second, and so on
        - Screenshots should always be an individual element in the dictionary as given in the JSON structure
        - Place ONE caption immediately after each screenshot
        - Captions should be plain text without any labels or prefixes

        3. Formatting rules:
        - No nested objects except as shown in the structure
        - No additional sections or fields
        - No markdown or special formatting in text
        - Use double quotes for strings
        - Ensure all strings are properly escaped

        Generate the documentation following these rules exactly."""
        
        try:
            response = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="mixtral-8x7b-32768",
                temperature=0.3
            )
            
            content = response.choices[0].message.content.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
            
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print("Raw response:", response.choices[0].message.content)
            raise

    def save_json_content(self, content_dict, base_filename):
        json_filename = f"{os.path.splitext(base_filename)[0]}.json"
        json_path = os.path.join(self.output_dir, json_filename)

        output_json = {
            "metadata": {
                "generated_date": datetime.datetime.now().isoformat(),
                "version": "1.0"
            },
            "content": content_dict
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(output_json, f, indent=2, ensure_ascii=False)
        
        return json_path
    
    def prepare_image(self, image_path, max_width=6*inch):
        img = PILImage.open(image_path)
        aspect = img.height / img.width
        
        width = min(max_width, 6*inch)
        height = width * aspect
        
        return Image(image_path, width=width, height=height)

    def generate_pdf(self, content_dict, screenshot_paths):
        print("Generating PDF...")

        output_path = os.path.join(self.output_dir, "product_description.pdf")
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        description = []

        title = Paragraph(content_dict["title"], self.styles["CustomHeading1"])
        description.append(title)
        description.append(Spacer(1, 20))
        
        for section in content_dict["sections"]:
            heading = Paragraph(section["heading"], self.styles["CustomHeading2"])
            description.append(heading)
            
            for item in section["content"]:
                if item.startswith("[[SCREENSHOT-"):
                    print("screenshot found!")
                    screenshot_num = int(item.split('-')[1].rstrip(']]')) - 1
                    if screenshot_num < len(screenshot_paths):
                        img = self.prepare_image(screenshot_paths[screenshot_num])
                        description.append(img)
                elif item.startswith('Figure '):
                    caption = Paragraph(item, self.styles["ImageCaption"])
                    description.append(caption)
                else:
                    para = Paragraph(item, self.styles["CustomBody"])
                    description.append(para)
                    description.append(Spacer(1, 12))
        
        doc.build(description)
        return output_path
    
    def generate(self, audio_path, screenshot_paths):
        os.makedirs(self.output_dir, exist_ok=True)
        
        transcript = self.process_audio(audio_path)
        content_dict = self.analyze_content(transcript, screenshot_paths)

        pdf_path = self.generate_pdf(content_dict, screenshot_paths)
        json_path = self.save_json_content(content_dict, "json_content")
        
        print(f"Documentation generated successfully!")
        print(f"PDF saved at: {pdf_path}")
        print(f"JSON saved at: {json_path}")
        
        return {
            "pdf_path": pdf_path,
            "json_path": json_path
        }

def main():
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ValueError("API_KEY is not set in the environment variables")

    output_dir = "output_files/"
    model = PDFDocGenerator(api_key, output_dir=output_dir)
    
    audio_path = "input_files/audio.mp3"
    screenshots = ["input_files/shot1.png", "input_files/shot2.png"]
    
    output_files = model.generate(
        audio_path, 
        screenshots
    )
    
    print("\nGenerated files:")
    print(f"PDF: {output_files['pdf_path']}")
    print(f"JSON: {output_files['json_path']}")

if __name__ == "__main__":
    main()