We want to test our newly developped document graph, agentic search and agent tragectories on the financench bechmark. 
We'll start first with a few files and questions, then increase their number. We want to test  the robustness of the solution, improve the tools and skills, anf go forward automatic improvement through evaluation of  the trajectories (not yet developped). 

Get inspiration from rfq_pricing project. 

Here a first plan:
- Download the dataset using hugging face lib, and cache  is somewhere.  We normmally have a HF account. 
```
from datasets import load_dataset
ds = load_dataset("PatronusAI/financebench") ```

- Download the 3 first PDF file. They are here : 
https://github.com/patronus-ai/financebench/tree/main/pdfs 

- Configure the workflow to transform these PDF into markdown, decompose in sections, create the document graph with the nodes for Documents, Section, etc. 

- Use Mistral OCR to create these Markdown.  Put them  in $ONEDRIVE/prj/financebench/markdown  directory (so they are saved). Other files can go in the data project dir

- Check that the graph look correct, with the document, the sections etc

- setup the DeepAgent with the skills to query the graph

- Launch the agent with the questions related to the file (from the financebench dataset) 

- Compare the output with the ground answer. Get the tragectory, and peform a first analysis.   Write a report with the outcome, and steps to improvement. 

We will stop here for that phase.  Nex phase wil be to test with more files from the benchmark, and progressively improve our agent.


