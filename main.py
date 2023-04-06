import base64
from io import BytesIO
from PIL import Image
from tqdm import tqdm
import PyPDF2
import os
import openai
import logging

def count_pages(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        return len(reader.pages)

def save_base64_as_pdf(base64_string, output_file):
    # Decode the base64 string
    decoded_data = base64.b64decode(base64_string)

    # Create a BytesIO object to handle the binary data in memory
    image_data = BytesIO(decoded_data)

    # Open the image using PIL
    image = Image.open(image_data)

    # Save the image as a PDF file
    image.save(output_file, "PDF")

if __name__ == "__main__":
    GPT_prompt_template = """
    Prompt: {dalle prompt}
    Summarize the following text and using the template above create a Dall-E prompt to generate a picture to accompany the text:
    """
    ### Setup
    pdf_writer = PyPDF2.PdfWriter()
    openai.api_key = os.getenv("OPEN_AI_TOKEN")
    pdf_path = input("Enter the path to the PDF file: ")

    logging.basicConfig(filename=f"{pdf_path[:-4]}.log", filemode='w', level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    ### Create directory to store images
    image_dir = f"{pdf_path[:-4]}-images"
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)

    ### Get page count and display to user
    page_count = count_pages(pdf_path)
    print(f"The total number of pages in the PDF file is: {page_count}")
    print("Starting...")

    ### Iterate over PDF generating images per page and inserting them into new PDF file
    for i in tqdm(range(page_count)):
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            page = reader.pages[i]
            page_text = page.extract_text()

            ### Write original PDF page to new PDF
            pdf_writer.add_page(page)

        ### Generate Dall-E prompt from GPT-3
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=f"{GPT_prompt_template} {page_text}",
            max_tokens=1000,
            temperature=0.3
        )
        dalle_prompt = response.choices[0].text.strip("\n") # type: ignore
        logging.info(dalle_prompt)

        ### Generate Dall-E image using the GPT-3 prompt
        try:
            image = openai.Image.create(
                prompt=dalle_prompt,
                n=1,
                size="512x512",
                response_format="b64_json"
            )
        except:
            logging.warning("Prompt did not work. Continuing...")
            pass
        
        ### Convert IMG from base64 encoded to PDF image and save locally
        b64_image = image.data[0].b64_json # type: ignore
        save_base64_as_pdf(b64_image, f"{image_dir}/image_page{i}.pdf")

        ### Write Image to new PDF
        pdf_writer.append(f"{image_dir}/image_page{i}.pdf")

    ### Generate full new PDF
    pdf_writer.write(f"{pdf_path[:-4]}-pikbook.pdf")
    pdf_writer.close()
