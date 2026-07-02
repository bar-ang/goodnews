from bs4 import BeautifulSoup, NavigableString

def trace(elem, func, *args, **kwargs):
    for child in list(elem.children):
        if child.name is not None:
            trace(child, func, *args, **kwargs)
        else:
            func(child, *args, **kwargs)

class HTMLManipulator:
    def __init__(self, html: str):
        self._soup = BeautifulSoup(html, 'html.parser')

    @property
    def root(self):
        return self._soup.body if self._soup.body else self._soup

    def replace_words(self, words):
        def _replace(child, words):
            mod_child = child
            for original, replace in words.items():
                mod_child = mod_child.replace(original, replace)
            child.replace_with(NavigableString(mod_child))

        trace(self.root, _replace, words)

    def reverse(self):
        def _reverse(child):
            child.replace_with(NavigableString(child[::-1]))

        trace(self.root, _reverse)

    def get(self):
        return self._soup



if __name__ == "__main__":
    html_content = open("debug_server/english.html", "r").read()
    htmlman = HTMLManipulator(html_content)
    htmlman.replace_words(dict(Travel="Bamba", of="IN", e="k"))
    print(htmlman.get().prettify())

    output_filename = "debug_server/index_replace.html"
    with open(output_filename, "w", encoding="utf-8") as file:
        file.write(str(htmlman.get()))

    html_content = open("debug_server/english.html", "r").read()
    htmlman = HTMLManipulator(html_content)
    htmlman.reverse()
    print(htmlman.get().prettify())
    output_filename = "debug_server/index_reverse.html"
    with open(output_filename, "w", encoding="utf-8") as file:
        file.write(str(htmlman.get()))


