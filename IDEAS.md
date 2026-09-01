

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

Clearly,  skills can be improved.


Also there has been many changes in the code. Have a look at it and see if it could be simplified, made more generic etc. 
(I want notably to test later our approach with the OfficeQA Pro benchmark. )





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

