import os
import base64
from pathlib import Path
from typing import List, TypedDict, Annotated
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.text_splitter import MarkdownTextSplitter
from langgraph.graph import StateGraph, END

from spire.doc import *
from spire.doc.common import *

# Load environment variables from .env file
load_dotenv()


def list_files(directory: str, extension: str) -> list[str]:
    """
    Lists all files in a directory with a given extension, using a regular expression.
    """
    fpath = Path(directory)
    # Compile a case-insensitive regex pattern to match the file extension.
    pattern = re.compile(f".*\\.{extension}$", re.IGNORECASE)
    
    # 1. Use glob() with a simple string pattern ('**/*') to find all files recursively.
    # 2. Then, filter that list using your regex pattern.
    files_list = [
        str(p) for p in fpath.glob('**/*') 
        if p.is_file() and pattern.match(p.name)
    ]
    return files_list


def convert_file_to_imgs(fpath: str, output_dir: str) -> List[str]:
    """
    Converts a document file to images, saving them in the specified output directory.
    Returns a list of file paths to the generated images.
    """
    print(f"Converting file: {fpath} to images...")
    document = Document()
    document.LoadFromFile(fpath)

    # create a subdirectory named after the file (without extension)
    file_stem = Path(fpath).stem
    subdir = Path(output_dir) / file_stem
    subdir.mkdir(parents=True, exist_ok=True)
    # use the subdirectory as the output directory for this file
    output_dir = str(subdir)

    image_paths = []
    for i in range(document.GetPageCount()):
        # convert image to PNG format
        image_stream = document.SaveImageToStreams(i, ImageType.Bitmap)

        # save PNG to output directory
        output_path = Path(output_dir) / f"{Path(fpath).stem}_page_{i + 1}.png"
        with open(output_path, 'wb') as img_file:
            img_file.write(image_stream.ToArray())
        image_paths.append(str(output_path))

    return image_paths


# --- 1. Define the State for the Workflow ---

class WorkflowState(TypedDict):
    """
    Defines the state that is passed between nodes in the workflow.
    """
    input_file: str
    output_dir: str
    image_paths: List[str]
    markdown_content: str
    chunks: List[str]
    error: str | None

# --- 2. Define the Nodes (Stages) for the Workflow ---

def doc_to_imgs_converter_node(state: WorkflowState) -> WorkflowState:
    """
    Node to convert the input document file to a series of images.
    This node acts as a wrapper around your existing tool.
    """
    print("--- Stage: Converting Document to Images ---")
    
    try:
        input_file = state["input_file"]
        output_dir = state["output_dir"]
        
        # Call the imported tool function
        image_paths = convert_file_to_imgs(input_file, output_dir)
        
        print(f"Successfully converted document to {len(image_paths)} images.")
        return {"image_paths": image_paths, "error": None}
    except Exception as e:
        print(f"ERROR in doc_to_imgs_converter_node: {e}")
        return {"error": f"Failed to convert document: {e}"}

def image_to_markdown_extractor_node(state: WorkflowState) -> WorkflowState:
    """
    Node to extract content from images and generate markdown using a vision LLM.
    """
    print("--- Stage: Extracting Content from Images to Markdown ---")
    try:
        image_paths = state["image_paths"]
        if not image_paths:
            raise ValueError("No image paths found in the state.")

        # Initialize the Gemini 2.5 Pro model
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=os.getenv("GOOGLE_API_KEY"))
        
        image_messages = []
        for img_path in image_paths:
            with open(img_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
                image_messages.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{encoded_image}"},
                })

        # Create the prompt for the vision model
        prompt = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "You are an expert document analyst. Analyze the following document pages (provided as images) and generate a single, clean, and well-structured markdown file representing the full content of the document. Preserve headings, lists, tables, and other formatting. Remove any watermarks or content related to spire.doc python package including warnings printed in RED color.",
                },
                *image_messages,
            ]
        )
        
        # Invoke the model
        response = llm.invoke([prompt])
        markdown_content = response.content
        
        print("Successfully extracted content to markdown.")
        return {"markdown_content": markdown_content, "error": None}
    except Exception as e:
        print(f"ERROR in image_to_markdown_extractor_node: {e}")
        return {"error": f"Failed to extract content from images: {e}"}

def markdown_chunker_node(state: WorkflowState) -> WorkflowState:
    """
    Node to chunk the generated markdown content.
    """
    print("--- Stage: Chunking Markdown Content ---")
    try:
        markdown_content = state["markdown_content"]
        if not markdown_content:
            raise ValueError("No markdown content found in the state.")
            
        # Use LangChain's MarkdownTextSplitter for adaptable chunking
        splitter = MarkdownTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = splitter.split_text(markdown_content)
        
        print(f"Successfully split markdown into {len(chunks)} chunks.")
        return {"chunks": chunks, "error": None}
    except Exception as e:
        print(f"ERROR in markdown_chunker_node: {e}")
        return {"error": f"Failed to chunk markdown: {e}"}

# --- 3. Define Conditional Logic for Error Handling ---

def should_continue(state: WorkflowState) -> str:
    """
    Determines the next step based on whether an error occurred.
    """
    if state.get("error"):
        print("--- Workflow failed. Halting execution. ---")
        return "end"
    return "continue"

# --- 4. Assemble the Workflow Graph ---

def build_workflow():
    """
    Builds and returns the LangGraph workflow.
    """
    workflow = StateGraph(WorkflowState)

    # Add nodes to the graph
    workflow.add_node("doc_converter", doc_to_imgs_converter_node)
    workflow.add_node("markdown_extractor", image_to_markdown_extractor_node)
    workflow.add_node("chunker", markdown_chunker_node)

    # Set the entry point
    workflow.set_entry_point("doc_converter")

    # Add conditional edges for error handling
    workflow.add_conditional_edges(
        "doc_converter",
        should_continue,
        {"continue": "markdown_extractor", "end": END},
    )
    workflow.add_conditional_edges(
        "markdown_extractor",
        should_continue,
        {"continue": "chunker", "end": END},
    )
    workflow.add_conditional_edges(
        "chunker",
        should_continue,
        {"continue": END, "end": END},
    )

    # Compile the graph
    return workflow.compile()

if __name__ == "__main__":
    # Define the input file and output directory
    input_doc = "<input your document file path here>"
    output_dir = "<output directory path here>"

    # Create the initial state
    initial_state = {
        "input_file": input_doc,
        "output_dir": output_dir,
    }

    # Build and run the workflow
    app = build_workflow()
    final_state = app.invoke(initial_state)

    # Print the final results
    print("\n--- Workflow Finished ---")
    if final_state.get("error"):
        print(f"Final Status: FAILED")
        print(f"Error Message: {final_state['error']}")
    else:
        print(f"Final Status: SUCCESS")
        print(f"Number of chunks created: {len(final_state.get('chunks', []))}")
        
        # Save the generated markdown to a file for inspection
        markdown_output_path = Path(output_dir) / "extracted_content.md"
        with open(markdown_output_path, "w", encoding="utf-8") as f:
            f.write(final_state.get("markdown_content", ""))
        print(f"Full markdown content saved to: {markdown_output_path}")
