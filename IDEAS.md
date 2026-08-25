# Improvement 

- The module that decompose a Markdown file into sections can be improved (called from cli docgraph build).  Today, some sections created have  no text.  One reason is that the PDF to Markdown process is sometime not able to discover the structure of the document (ex if no formal, numered titles), so all is level 1.  
But usually the document has a table of content at the begining, that could be used for the breakdown into section. Structure can also sometime be deduced from style change.
That could be used, either programmatically or through an LLM.

However, an LLM is already used for summarization. It takes a Markdown, annotated with sections separation calculated algorithm. We could improve make it also discover the document structure...  

Here my idea: 
A/  There could be 2 workflows for docgraph build : 
    1/ The currect one, algo only, rapid, without LLM  
    2/ A better one, with algo and LLM.

The workflow for the 2nd (with LLM)  could take a Markdown file and produce a JSON file with the table of content of the document (compatible with one extracted by algorithm only )  + the summary of each sections (as done by separate commmand cli docgraph summarize  - that can be removed). We could later add more information , such as keywords, entities, etc. 
It is imortant not to put the content of each section in that JSON, to reduce output token. the merge between that JSON and the original Markdown will to produce the graph nodes is  be done at a later stage.
We take the assumption that the LLM is a 'flash' one, ie cheap, with limited reasonning capabilities, and able to accept 1M token. Warn the user if the number of taken in the document is greater than the context window of the provided LLM and don't process the file (we will handle this unlikely case later, possibly)

Think, Think, propose a plan, ask questions, suggest alternatives, ...












The pattern is usually 

# **Liquidity and Capital Resources Risks**

# ***The agreements governing our notes, our guarantees of the Assumed Xilinx Notes, and our Revolving Credit Agreement impose restrictions on us that may adversely affect our ability to operate our business.***

bla bla 

*Our indebtedness could adversely affect our financial position and prevent us from implementing our strategy or fulfilling our contractual obligations.*

Our total debt pri



- Almost Empty sections : ex cli docgraph cat f391da52bf0af1c2::135
   -> to merge 
   - See with summaries process

- need better 'docgraph cat' commmand -> section range, section separator 

- There' other financial doc than 10K and 100 K  : EArnings, Annual Report, 8K, 10Q, 
    -> Update skills

- No summaries -   cli docgraph toc f391da52bf0af1c2 --yaml 
    Does that has an impact ? Measure it

- Summaries or embeddings of section ? 

- cli trajectory view  don't work

-  cli trajectory list -> only run-id: expected grouping per session-id 

- cli-graph as a plugin of genai-tk ? More plugins ? (Prefect ? BAML ? DeerFlow ? ) 

- Test with Harbor ?   (need one DB per session  ? ) 

- Compare with NanoNet, PageIndex, Mistral Agentic Search https://mistral.ai/news/agentic-search/
  https://huggingface.co/datasets/databricks/officeqa 
  https://arxiv.org/abs/2603.08655 

- Main (budget) Nassime (200 €) ; argument comparaison avec Mistral ...  


- better workflow to combine markdownieation with summary (+Glinner ? )
   -> Create a YAML file ?   or OKG ?  Of GrapgDB, then file
   extract entities ?  Linkk them to wikipedia / dbpedia / ...  ? 


   Gliner ?    https://github.com/neuml/gliner   ? https://github.com/Knowledgator/GLinker 
   or during summarization process ? 

Markdown -> Sections -> Summarization


https://github.com/VectifyAI/Mafin2.5-FinanceBench/blob/main/eval.py

