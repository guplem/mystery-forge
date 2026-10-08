Look at every page of the rendered game like a player who just printed it. The page images are in `{{ steps.render.json.previews_dir }}` (one PNG per printed page: the manual, the materials, the hints, and the solutions). Open each image with your file reading tool and look at it.

Report a problem when a page:
- is hard to read (tiny or cramped text, low contrast, text over a busy background), or text runs into the edge or another element;
- looks broken (an empty page, a stray mark, a puzzle grid cut in half, a caption without its image, an image that is a black box);
- looks cheap or does not match its document kind (a "newspaper" that looks like a plain letter);
- has a hint card or a solution step that names something (a picture, a mark, an arrow, a symbol, a position) that the materials page of its puzzle does not show; name both pages;
- spoils something: a hint or an answer visible on a materials page, or on the first page of the hints or the solutions file;
- wastes paper: a nearly empty page that a small change would remove.

A finding is `required` when it makes the game harder to play or spoils it. Everything else is a `suggestion`. Name the page by its image file name, and give a concrete fix in the source files (shorter text, a page break, another document kind, a smaller image). Return an empty list when every page looks right. Do not change any file.
