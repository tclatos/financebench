
# OfficeQA_pro

We want to adapt our FinanceBench work on the OfficeQA PRO benchmark.
It is described here: 
https://huggingface.co/datasets/databricks/officeqa 

We will try to use the transformed dataset, to avoid OCR costs, and taking advantage that we have now a tree_parser that can takes files without Markdown marks.
It is available https://huggingface.co/datasets/databricks/officeqa/tree/main/treasury_bulletins_parsed/transformed 

The Hugging Face API key is in the .env. 
I've already accepted the conditions to access the dataset.

Here the first phase I suggest :


1/ create a /home/tcl/prj/officeqa folder and fork https://github.com/tclatos/financebench there

2/ rename everything looking at 'financebench' to 'officeqa'. Do a quick test that 'cli --help' list available commands without error

3/ Adapt code to use question datasets and files from the HF databricks/officeqa repo

4/ Take one file (any) and see if our tree_parsing algo (in /home/tcl/prj/genai-graph/genai_graph/kg/document_graph/tree_parser.py) works well, ie that the document is decomposed in several sections that makes sense and are correctly inserted in the graph db. Update code if required (but try not to break it - it works correctly for financeweb...).
If you assess that it can work that way, stop here ( We will the OCR approach).

5/ Do not calculate embedding, BM25 index etc for now. It will next phases.



# Review 

Review the first iterations to achieve good results at FinanceBench. I want to get your view before trying with stronger LLM, and continuing evaluation with more files from the benchmark.
- Analyse the reports here  : /home/tcl/prj/financebench/report
- Analyse directly the recorded trajectories: /home/tcl/prj/financebench/data/trajectories 
- Analyse code and skills (genai-graph and financebech) 
Make your own critical analysis of what has been done, and what could be improved.
  
- https://github.com/NanoNets/nanoindex/ 
- https://github.com/VectifyAI/Mafin2.5-FinanceBench  (based on https://github.com/VectifyAI/PageIndex).  
Is  there other reason than using stronger LLM ? 



- need better 'docgraph cat' commmand -> section range, section separator 

- There are other financial docs than 10-K: Earnings Releases, Annual Reports, 8-K, 10-Q, 20-F/6-K
    -> Update skills & system prompt [DONE: expanded financebench-qa skill and agents.yaml system prompt with filing-type routing, 8-K exhibits, 10-Q quarter vs YTD, notes drilldown, and trajectory insights]
    Does that has an impact ? Measure it

- Summaries or embeddings of section ? 

- cli trajectory view  don't work

-  cli trajectory list -> only run-id: expected grouping per session-id 

- cli-graph as a plugin of genai-tk ? More plugins ? (Prefect ? BAML ? DeerFlow ? ) 

- Test with Harbor ?   (need one DB per session  ? ) 

- Compare with NanoIndex, PageIndex, Mistral Agentic Search https://mistral.ai/news/agentic-search/
https://github.com/NanoNets/nanoindex 

  https://huggingface.co/datasets/databricks/officeqa 
  https://arxiv.org/abs/2603.08655 

- Utiliser https://github.com/NanoNets/nanoindex/blob/main/nanoindex/knowledge/financial_kb.json ? 


- Main (budget) Nassime (200 €) ; argument comparaison avec Mistral ...  


- better workflow to combine markdownieation with summary (+Glinner ? )
   -> Create a YAML file ?   or OKG ?  Of GrapgDB, then file
   extract entities ?  Linkk them to wikipedia / dbpedia / ...  ? 


   Gliner ?    https://github.com/neuml/gliner   ? https://github.com/Knowledgator/GLinker 
   or during summarization process ? 

Markdown -> Sections -> Summarization


https://github.com/VectifyAI/Mafin2.5-FinanceBench/blob/main/eval.py

