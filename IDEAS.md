

# Use 
 - latest deepseek-v4-flash-7XXX
 - GLM 5.2 (as Mistral memo)



# better genai-graph

- Update in genai-graph  the  cli docgraph commands so that they  take into account the new feature related to chunks

- Use Chonkie instead of genai_graph/kg/document_graph/chunker.py 

- Have a YAML file to define how the doc graph is build. Reuse the build part of /home/tcl/prj/financebench/config/bench.yaml. Define several configs (fulln withour embeddings, ...) and a default one as a YAML alias.

- more tests, notably semantic  search. Create test graph in memory ;   Use real LLM

- update doc and skills


# better financebench
- leverage the changes in genai-graph


Update doc 

# Review 

Review the first iterations to achieve good results at FinanceBench. I want to get your view before trying with stronger LLM, and continuing evaluation with more files from the benchmark.
- Analyse the reports here  : /home/tcl/prj/financebench/report
- Analyse directly the recorded trajectories: /home/tcl/prj/financebench/data/trajectories 
- Analyse code and skills (genai-graph and financebech) 
Make your own critical analysis of what has been done, and what could be improved.
Progress has notably been done when moving away from a pure solution without embeddings. It's not a major concern because I'm not a purist and having embeddings does not impact design too much and could be useful anyway, but I would like to understand how other solutions claim very good results with just doc tree:   
- https://github.com/NanoNets/nanoindex/ 
- https://github.com/VectifyAI/Mafin2.5-FinanceBench  (based on https://github.com/VectifyAI/PageIndex).  
Is  there other reason than using stronger LLM ? 

I also wonder why the search tool is so used. Is the table of content not enough informative (could we improve the process to pass from Markdow doc to sections ? the summaries ? ) ? or the skill not providing correct approach  ? 

I also think that reading financial_kb.json from a skill is useless - we could but the knowledge inside the skill in markdown. 
Clearly,  skills can be improved.

The CLi command tu run the test could be in Python rather than in just, to more compliant with other commmands

Also there has been many changes in the code. Have a look at it and see if it could be simplified, made more generic etc. 
(I want notably to test later our approach with the OfficeQA Pro benchmark. )















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

