import json
import re
import os
import io
import collections
from PIL import Image, ImageOps
from html_parser import HTMLManipulator
from mitmproxy import http
from mitmproxy import ctx

def reset_field(fields, target_key, new_value):
    # Ensure target_key is bytes for comparison (assuming input fields use bytes keys)
    if isinstance(target_key, str):
        target_key_bytes = target_key.encode('utf-8')
    else:
        target_key_bytes = target_key

    # Lowercase the target key for case-insensitive matching
    target_key_lower = target_key_bytes.lower()

    # Ensure the new value is converted to bytes
    if isinstance(new_value, (int, float)):
        new_value_bytes = str(int(new_value)).encode('utf-8')
    elif isinstance(new_value, str):
        new_value_bytes = new_value.encode('utf-8')
    elif isinstance(new_value, bytes):
        new_value_bytes = new_value
    else:
        new_value_bytes = str(new_value).encode('utf-8')

    updated_fields = []
    key_found = False

    for key, val in fields:
        # Check if the current header matches our target (case-insensitive)
        if key.lower() == target_key_lower:
            updated_fields.append((key, new_value_bytes))
            key_found = True
        else:
            updated_fields.append((key, val))

    # Raise an error if the header was never encountered
    if not key_found:
        raise KeyError(f"Header '{target_key}' not found in the provided fields.")

    return tuple(updated_fields)

def invert_image_colors(img):
    # 2. Handle transparency if it's a PNG with an Alpha channel (RGBA)
    if img.mode == 'RGBA':
        # Split into Red, Green, Blue, and Alpha channels
        r, g, b, a = img.split()
        # Merge the RGB channels back together to invert them
        rgb_img = Image.merge('RGB', (r, g, b))
        inverted_rgb = ImageOps.invert(rgb_img)
        # Split the inverted RGB channels and re-attach the original Alpha channel
        r2, g2, b2 = inverted_rgb.split()
        final_img = Image.merge('RGBA', (r2, g2, b2, a))
    else:
        # If it doesn't have transparency (e.g., standard RGB), invert directly
        # If it's a grayscale 'P' mode or 'L', convert to RGB first
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        final_img = ImageOps.invert(img)

    return final_img

def update_word_frequencies(new_words_list: list, json_file_path: str):
    # 1. Load existing data or initialize an empty dict if the file doesn't exist
    if os.path.exists(json_file_path) and os.path.getsize(json_file_path) > 0:
        with open(json_file_path, "r", encoding="utf-8") as f:
            try:
                frequency_map = json.load(f)
            except json.JSONDecodeError:
                # Fallback if the JSON file is corrupted
                frequency_map = {}
    else:
        frequency_map = {}

    # 2. Count frequencies of the new words efficiently using Counter
    new_counts = collections.Counter(new_words_list)

    # 3. Update the map (handles both existing keys and new keys)
    for word, count in new_counts.items():
        # Ensure the key exists as an integer, then add the new count
        frequency_map[word] = frequency_map.get(word, 0) + count

    sorted_frequencies = dict(
        sorted(frequency_map.items(), key=lambda x: x[1], reverse=True)
    )

    # 4. Save the updated map back to the JSON file
    with open(json_file_path, "w", encoding="utf-8") as f:
        # ensure_ascii=False keeps Hebrew/Unicode readable inside the JSON file
        json.dump(sorted_frequencies, f, ensure_ascii=False, indent=4)

def extract_visible_words(html_code: str) -> str:
    # Parse the HTML content
    soup = BeautifulSoup(html_code, "html.parser")

    # Remove all invisible elements, scripts, and styles
    for element in soup(["script", "style", "meta", "noscript", "header", "footer"]):
        element.decompose()

    # Extract all text, including titles/headings
    visible_text = soup.get_text(separator=" ")

    # Use regex to find all words (matches alphanumeric sequences)
    # This also handles Hebrew and other non-English alphabets smoothly
    words = re.findall(r"\b\w+\b", visible_text)

    # Return the list compiled into a JSON string
    return words

IMAGE_MANIPULATION_MODES = {
    "none" : "do not change images",
    "gallery" : "choose random image from gallery",
    "invert": "invert image colors"
}
TEXT_MANIPULATION_MODES = {
    "none" : "do not change texts",
    "replace" : "replace words with funnier words",
    "reverse": "reverse characters in text"
}

def replace_words(text: str, replacements) -> str:
    for original, replacement in replacements.items():
        text = text.replace(original, replacement)

    return text

class MyFirstAddon:
    #def __init__(self, domains_file="domains.txt", words_file="replace.txt"):
    #    self._domains = self.load_domains(domains_file)
    #    self._images = [Image.open("gallery/textisempty.jpg")]
    #    self._replace_words = self.load_replace_words(words_file)

    def load(self, loader, domains_file="domains.txt", words_file="replace.txt"):
        self._domains = self.load_domains(domains_file)
        self._images = [Image.open("gallery/textisempty.jpg")]
        self._replace_words = self.load_replace_words(words_file)
        loader.add_option(
            name="dev_mode",
            typespec=bool,
            default=False,
            help="Alter only localhost sites",
        )
        loader.add_option(
            name="image_mode",
            typespec=str,
            default="none",
            help=", ".join([f"{k}={v}" for k, v in IMAGE_MANIPULATION_MODES.items()]),
        )
        loader.add_option(
            name="text_mode",
            typespec=str,
            default="replace",
            help=", ".join([f"{k}={v}" for k, v in TEXT_MANIPULATION_MODES.items()]),
        )

    def running(self):
        print(f"ADDON LOADED, LISTED DOMAINS: {self._domains}")
        if ctx.options.text_mode not in TEXT_MANIPULATION_MODES.keys():
            info = ", ".join([f"{k}={v}" for k, v in TEXT_MANIPULATION_MODES.items()])
            raise Exception(f"Unknown text manipulation mode '{ctx.options.text_mode}'.\nAvailable modes: {info}")
        print(f"Text manipulation mode: {ctx.options.text_mode}")

        if ctx.options.image_mode not in IMAGE_MANIPULATION_MODES.keys():
            info = ", ".join([f"{k}={v}" for k, v in IMAGE_MANIPULATION_MODES.items()])
            raise Exception(f"Unknown image manipulation mode '{ctx.options.image_mode}'.\nAvailable modes: {info}")
        print(f"Image manipulation mode: {ctx.options.image_mode}")


    def load_domains(self, file, comment="#"):
        res = []
        with open(file, "r") as f:
            for line in f:
                line = line.strip()
                if line and line[0]!=comment:
                    res.append(line)
        return res


    def load_replace_words(self, file, delim=":", comment="#"):
        with open(file, "r") as f:
            replacements = {}

            for line in f:
                line = line.strip()
                if not line or ':' not in line or line[0]==comment:
                    continue

                original, replacement = line.split(delim, 1)
                replacements[original.strip()] = replacement.strip()
        return replacements


    def request(self, flow: http.HTTPFlow) -> None:
        """
        This function triggers whenever your computer sends a REQUEST to a server.
        """
        # Log the target URL to your terminal
        #print(f"[--> REQUEST] Browser is visiting: {flow.request.pretty_url}")


    def response(self, flow: http.HTTPFlow) -> None:
        """
        This function triggers whenever a server sends a RESPONSE back to your computer.
        """
        try:
            host = flow.server_conn.address[0]
        except TypeError:
            host = flow.request.data.headers["Host"].split(":")[0]

        if ctx.options.dev_mode and not host=="localhost":
            return

        if not host in self._domains:
            return

        print("LISTED", host)

        with open("replace.txt", 'r', encoding='utf-8') as file:
            content_type = flow.response.headers.get("content-type", "")
            if "text/html" in content_type:
                print("GOT HTML", content_type)
                if ctx.options.text_mode == "replace":
                    textman = HTMLManipulator(flow.response.text)
                    textman.replace_words(self._replace_words)
                    #update_word_frequencies(extract_visible_words(text), "freqs.json")
                    flow.response.text = str(textman.get())
                elif ctx.options.text_mode == "reverse":
                    textman = HTMLManipulator(flow.response.text)
                    textman.reverse()
                    flow.response.text = str(textman.get())
                else:
                    pass
            elif "application/json" in content_type:
                print("GOT JSON", content_type)
                clean = flow.response.text.replace("jsonCallback(", "").replace(");", "")
                t2 = json.loads(clean)
                try:
                    text = json.dumps(t2, ensure_ascii=False)
                except Exception as e:
                    print(e)
                    text=t2
                flow.response.text = replace_words(text, self._replace_words)
            elif "image" in content_type:
                print("GOT IMG", content_type)
                im_type = content_type.split("/")[1]
                if im_type not in ["png", "jpg", "jpeg", "avif", "gif"]:
                    return

                if flow.response.data.status_code != 200:
                    print(f"GOT STATUS {flow.response.data.status_code}")
                    return

                if ctx.options.image_mode == "gallery":
                    replace_image = Image.open("gallery/textisempty.jpg")
                    im_type = content_type.split("/")[1]
                    if im_type in ["png", "jpg", "jpeg", "avif", "gif"]:
                        if flow.response.data.status_code != 200:
                            print(f"GOT STATUS {flow.response.data.status_code}")
                            return
                        output_bytes = io.BytesIO()
                        replace_image.save(output_bytes, format="JPEG")
                        flow.response.data.content = output_bytes.getvalue()
                        fields = flow.response.headers.fields
                        fields = reset_field(fields, 'Content-Length', output_bytes.tell())
                        fields = reset_field(fields, 'Content-Type', "image/jpeg")
                        flow.response.headers.fields = fields
                elif ctx.options.image_mode == "invert":
                    if len(flow.response.data.content) < 4000:
                        return
                    image_stream = io.BytesIO(flow.response.data.content)
                    img = Image.open(image_stream)

                    invimg = invert_image_colors(img)
                    #Save it back into bytes to send over the network
                    output_bytes = io.BytesIO()
                    invimg.save(output_bytes, format=im_type.upper())
                    flow.response.data.content = output_bytes.getvalue()
                elif ctx.options.image_mode == "none":
                    pass
                else:
                    print(f"UNKNOWN IMAGE MANIPULATION MODE: {ctx.options.image_mode}")
            else:
                print("GOT UNHANDLED CONTENT TYPE", content_type)

# This list registers your class with mitmproxy so it knows to execute it
addons = [
    MyFirstAddon()
]
