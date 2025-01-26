import re
import os
import io
import replicate
import requests
from datetime import datetime
from PIL import Image
import openai
import logging

from .utils import clean_title, compress_image
from .config import client, config



def get_prompts():
    directory_path = config['folders']['prompts']
    prompts = {}
    
    for filename in os.listdir(directory_path):
        if not filename.endswith('.txt'):
            continue
            
        basename = filename.split('.')[0]
        file_path = os.path.join(directory_path, filename)
        
        with open(file_path, 'r') as file:
            if '.system.txt' in filename:
                if basename not in prompts:
                    prompts[basename] = {}
                prompts[basename]['system'] = file.read()
            elif '.user.txt' in filename:
                if basename not in prompts:
                    prompts[basename] = {}
                prompts[basename]['user'] = file.read()
            else:
                prompts[basename] = file.read()
    return prompts

prompts=get_prompts()

def generate_content(prompt_name, data={}):
    messages = []
    print (prompt_name)
    try:
        logging.info(f"Generating content with data: {data}")

        # Validate prompt existence
        if prompt_name not in prompts:
            logging.error(f"Prompt '{prompt_name}' not found in available prompts.")
            return None

        prompt = prompts[prompt_name]

        # Extract placeholders from the prompt
        def extract_placeholders(prompt_text):
            return re.findall(r'{(.*?)}', prompt_text)

        required_keys = set()
        if isinstance(prompt, dict):
            if 'user' in prompt:
                required_keys.update(extract_placeholders(prompt['user']))
        else:
            required_keys.update(extract_placeholders(prompt))

        # Check if all required keys are present in the data
        missing_keys = required_keys - set(data.keys())
        if missing_keys:
            logging.error(f"Missing required data keys for formatting: {missing_keys}")
            return None

        # Build messages based on prompt structure
        if isinstance(prompt, dict):
            if 'system' in prompt:
                messages.append({
                    "role": "system",
                    "content": prompt['system']
                })
            if 'user' in prompt:
                messages.append({
                    "role": "user",
                    "content": prompt['user'].format(**data)
                })
        else:
            messages.append({
                "role": "user",
                "content": prompt.format(**data)
            })

        # Send request to the OpenAI client
        response = client.chat.completions.create(
            model=config['openai']['llm-model'],
            messages=messages
        )

        result = response.choices[0].message.content.strip()
        logging.info("Content generation successful.")
        return result

    except KeyError as key_err:
        logging.error(f"KeyError: Missing data for formatting - {key_err}")
    except Exception as ex:
        logging.error(f"Error during content generation: {ex}")

    return None

def generate_art_prompt(title):
    if config['img_src']=="flux":
        return generate_content('flux',{'title':title})
        
    elif config['img_src']=="dalle":
        return generate_content('dalle',{'title':title})
    else:
        print("No IMG Source configured")
        return



def generate_image(title):
    prompt=generate_art_prompt(title)
    cleaned_title = clean_title(title)
    if config['img_src']=="flux":
        img = create_flux_pro_image(prompt, cleaned_title)
    elif config['img_src']=="dalle":
        img = create_dalle_image(prompt, cleaned_title)
    else:
        print("No IMG Source configured")
        return
    return img


def create_dalle_image(image_desc, title):
    print('\nImage Prompt:',image_desc,'\nTitle:',title)
    
    response = client.images.generate(
        model="dall-e-3",
        prompt=image_desc,
        size="1024x1024",
        quality="standard",
        n=1,
        )

    image_url = response.data[0].url

    image_data = requests.get(image_url).content

    # Clean and sanitize the title
    cleaned_title = clean_title(title)
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    image_filename = f"{current_datetime}-{cleaned_title}.png"

    image_path = os.path.join(config['folders']['images'], image_filename)
    with open(image_path, "wb") as f:
        f.write(image_data)
    return image_path




# Function to create an image using FLUX PRO
def create_flux_pro_image(file_name,  folder, prompt,file_type="webp", target_width=512, target_height=512, crop=False, resize=False):
    print("Creating image with FLUX PRO...")

    ASPECT_RATIOS = {
        "1:1": (1, 1),
        "16:9": (16, 9),
        "3:2": (3, 2),
        "2:3": (2, 3),
        "4:5": (4, 5),
        "5:4": (5, 4),
        "9:16": (9, 16),
        "3:4": (3, 4),
        "4:3": (4, 3)
    }

    aspect = target_width / target_height
    closest_ratio = "custom"

    for ratio, dims in ASPECT_RATIOS.items():
        ratio_value = dims[0] / dims[1]
        if abs(ratio_value - aspect) < 1e-10:
            closest_ratio = ratio
            break

    replicate_config=config['replicate']
    flux_config = {
        "prompt": prompt,
        "width": target_width,
        "height": target_height,
        "aspect_ratio": closest_ratio,
        "prompt_upsampling": replicate_config.get('prompt_upsampling', True),
        "output_format": replicate_config.get('output_format', 'png'),
        "num_inference_steps": replicate_config.get('num_inference_steps', 50),
        "guidance_scale": replicate_config.get('guidance_scale', 7.5),
    }
    replicate_client=replicate.Client(api_token=replicate_config['api_key'])
    
    output = replicate_client.run(
        replicate_config['image-model'],
        input=flux_config
    )
    
    image_data = output.read()
    image = Image.open(io.BytesIO(image_data))

    # Resize if flag is enabled
    if resize:
        current_ratio = image.width / image.height
        target_ratio = target_width / target_height

        if current_ratio > target_ratio:
            # Image is too wide, scale by height
            new_height = target_height
            new_width = int(target_height * current_ratio)
        else:
            # Image is too tall, scale by width
            new_width = target_width
            new_height = int(target_width / current_ratio)

        image = image.resize((new_width, new_height), Image.LANCZOS)

    # Crop if flag is enabled
    if crop:
        left = (image.width - target_width) // 2
        top = (image.height - target_height) // 2
        image = image.crop((left, top, left + target_width, top + target_height))

    # Validate file type and save image
    valid_file_types = ["png", "jpeg", "jpg", "bmp", "webp"]
    file_type = file_type.lower()
    if file_type not in valid_file_types:
        raise ValueError(f"Unsupported file type: {file_type}. Supported types are: {', '.join(valid_file_types)}")

    os.makedirs(os.path.dirname(file_name), exist_ok=True)

    # Ensure correct file extension
    output_path = os.path.splitext(file_name)[0] + f".{file_type}"
    image.save(output_path, file_type.upper())

    return output_path
