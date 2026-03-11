"use client";

import { useState, useEffect } from "react";
import { 
  Search, Loader2, FileText, CheckCircle2, AlertCircle, 
  ImageIcon, Folder, Plus, ChevronRight, LayoutDashboard, 
  Settings, History, Save, Download
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface JobStatus {
  job_id: string;
  status: string;
  progress: number;
  message: string;
  result?: any;
}

export default function Dashboard() {
  const [url, setUrl] = useState("");
  const [activeArea, setActiveArea] = useState("Geral");
  const [savedAreas, setSavedAreas] = useState<string[]>(["Geral", "Retina", "Glaucoma", "Córnea"]);
  const [isAddingArea, setIsAddingArea] = useState(false);
  const [newAreaName, setNewAreaName] = useState("");
  
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [isSaved, setIsSaved] = useState(false);

  // Load saved areas on mount
  useEffect(() => {
    const areas = localStorage.getItem("eyearticle_areas");
    if (areas) {
      setSavedAreas(JSON.parse(areas));
    }
  }, []);

  const addArea = () => {
    if (newAreaName && !savedAreas.includes(newAreaName)) {
      const newAreas = [...savedAreas, newAreaName];
      setSavedAreas(newAreas);
      localStorage.setItem("eyearticle_areas", JSON.stringify(newAreas));
      setNewAreaName("");
      setIsAddingArea(false);
    }
  };

  const startResearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) return;

    setLoading(true);
    setJobId(null);
    setStatus(null);
    setIsSaved(false);

    try {
      const resp = await fetch(`${API_BASE}/api/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, disease_label: activeArea }),
      });
      const data = await resp.json();
      setJobId(data.job_id);
    } catch (err) {
      console.error(err);
      alert("Falha ao conectar com o servidor.");
      setLoading(false);
    }
  };

  const saveToArea = async (area: string) => {
    if (!jobId || !status?.result) return;
    
    try {
      const resp = await fetch(`${API_BASE}/api/save-to-area`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId, area_name: area }),
      });
      const data = await resp.json();
      if (data.status === "success" || data.status === "already_saved") {
         setStatus(prev => {
           if (!prev || !prev.result) return prev;
           return {
             ...prev,
             result: {
               ...prev.result,
               safe_name: data.safe_name
             }
           };
         });
         setIsSaved(true);
         setActiveArea(area);
      }
    } catch (err) {
      console.error(err);
      alert("Erro ao salvar resumo na pasta escolhida.");
    }
  };

  useEffect(() => {
    if (!jobId) return;

    const interval = setInterval(async () => {
      try {
        const resp = await fetch(`${API_BASE}/api/status/${jobId}`);
        const data = await resp.json();
        setStatus(data);

        if (data.status === "completed" || data.status === "failed") {
          clearInterval(interval);
          setLoading(false);
        }
      } catch (err) {
        console.error(err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId]);

  return (
    <div className="flex min-h-screen bg-slate-50 font-sans">
      {/* Sidebar */}
      <aside className="w-72 bg-white border-r border-slate-200 flex flex-col hidden md:flex sticky top-0 h-screen overflow-hidden">
        <div className="p-8">
           <h1 className="text-2xl font-heading font-black text-slate-900 tracking-tight flex items-center gap-2">
            <span className="bg-blue-600 text-white w-8 h-8 rounded-lg flex items-center justify-center text-xs">EP</span>
            EyeArticle <span className="text-blue-600 italic">PRO</span>
          </h1>
        </div>

        <nav className="flex-1 px-4 space-y-8 overflow-y-auto">
          <div>
            <div className="flex items-center justify-between mb-4 px-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
              <span>Áreas de Pesquisa</span>
              <button onClick={() => setIsAddingArea(!isAddingArea)} className="hover:text-blue-600 transition-colors">
                <Plus className="w-4 h-4" />
              </button>
            </div>
            
            <div className="space-y-1">
              {isAddingArea && (
                <div className="px-4 mb-3">
                  <input 
                    autoFocus
                    className="w-full bg-slate-100 border-none rounded-lg px-3 py-2 text-sm focus:ring-2 ring-blue-500 outline-none"
                    placeholder="Área (Ex: Retina)"
                    value={newAreaName}
                    onChange={e => setNewAreaName(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && addArea()}
                  />
                </div>
              )}
              {savedAreas.map(area => (
                <button
                  key={area}
                  onClick={() => setActiveArea(area)}
                  className={cn(
                    "w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all group",
                    activeArea === area 
                      ? "bg-blue-50 text-blue-700 shadow-sm shadow-blue-100" 
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  )}
                >
                  <Folder className={cn(
                    "w-4 h-4 transition-colors",
                    activeArea === area ? "text-blue-600" : "text-slate-400 group-hover:text-slate-600"
                  )} />
                  {area}
                  {activeArea === area && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-blue-600" />}
                </button>
              ))}
            </div>
          </div>

          <div>
             <div className="mb-4 px-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Atalhos</div>
             <div className="space-y-1">
                <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-50">
                  <History className="w-4 h-4 text-slate-400" /> Histórico
                </button>
                <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-50">
                  <Settings className="w-4 h-4 text-slate-400" /> Configurações
                </button>
             </div>
          </div>
        </nav>

        <div className="p-6">
          <div className="bg-slate-900 rounded-[2rem] p-5 text-white">
            <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">Local de gravação</p>
            <p className="font-bold text-sm truncate">{activeArea}</p>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto p-6 md:p-12 space-y-12">
          {/* Hero */}
          <section className="space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 text-blue-700 text-[10px] font-black uppercase tracking-wider">
              <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
              Engine v2.0 • IA Analysis
            </div>
            <h2 className="text-3xl md:text-4xl font-heading font-black text-slate-900 leading-tight">
              Análise Clínica de <span className="text-blue-600 underline underline-offset-8 decoration-blue-100 italic">Alta Precisão</span>.
            </h2>
            <p className="text-lg text-slate-600 max-w-xl font-body">
              Insira o link do PDF acadêmico para gerar um resumo clínico premium e visual.
            </p>

            <form onSubmit={startResearch} className="pt-4">
              <div className="relative group max-w-3xl">
                <input
                  type="url"
                  placeholder="Cole o link direto do PDF..."
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  className="w-full px-8 py-5 rounded-[2.5rem] border-2 border-slate-200 focus:border-blue-500 outline-none transition-all shadow-sm group-hover:shadow-md font-body text-lg pl-16 pr-36"
                  disabled={loading}
                  required
                />
                <FileText className="absolute left-7 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
                <button
                  type="submit"
                  disabled={loading || !url}
                  className="absolute right-4 top-1/2 -translate-y-1/2 bg-blue-600 hover:bg-blue-700 text-white px-8 py-3.5 rounded-2xl font-bold transition-all disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-blue-100 active:scale-95"
                >
                  {loading ? <Loader2 className="animate-spin w-5 h-5" /> : "Analisar"}
                </button>
              </div>
            </form>
          </section>

          {/* Progress & Result */}
          <AnimatePresence mode="wait">
            {status && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="space-y-10"
              >
                {(status.status === "queued" || status.status === "processing") && (
                  <div className="glass rounded-[3rem] p-12 text-center space-y-6">
                    <div className="relative w-24 h-24 mx-auto">
                       <div className="absolute inset-0 rounded-full border-4 border-slate-100" />
                       <div className="absolute inset-0 rounded-full border-4 border-blue-600 border-t-transparent animate-spin" />
                    </div>
                    <div>
                      <h3 className="text-xl font-black text-slate-900 mb-2">Processando Artigo...</h3>
                      <p className="text-slate-500 font-medium">{status.message}</p>
                    </div>
                    <div className="max-w-md mx-auto h-2 bg-slate-100 rounded-full overflow-hidden">
                       <motion.div 
                         className="h-full bg-blue-600"
                         initial={{ width: 0 }}
                         animate={{ width: `${status.progress}%` }}
                       />
                    </div>
                  </div>
                )}

                {status.status === "failed" && (
                  <div className="bg-red-50 border border-red-200 text-red-700 p-8 rounded-[2rem] flex gap-4 items-start">
                    <AlertCircle className="shrink-0 w-8 h-8" />
                    <div>
                      <p className="font-black text-lg">Falha na Análise</p>
                      <p className="opacity-80 mt-1">{status.message}</p>
                    </div>
                  </div>
                )}

                {status.status === "completed" && status.result && (
                  <div className="grid grid-cols-1 lg:grid-cols-4 gap-8 pb-32">
                    {/* Metadata Sidebar */}
                    <div className="lg:col-span-1 space-y-6">
                      <div className="glass rounded-[2rem] p-6 space-y-6">
                        <div className="flex flex-col gap-4">
                           <div className="flex items-center gap-2 text-green-600 font-bold">
                             <CheckCircle2 className="w-5 h-5" /> Analisado
                           </div>
                           <div>
                              <p className="text-sm font-black text-slate-900 leading-tight mb-2 line-clamp-4">{status.result.metadata?.title || "Sem título"}</p>
                              <p className="text-xs text-slate-500 font-medium">{status.result.metadata?.authors || "Autores não identificados"}</p>
                              <p className="text-xs text-slate-400 mt-1 font-bold">{status.result.metadata?.year || "N/A"}</p>
                           </div>
                        </div>

                        <div className="pt-4 border-t border-slate-100 space-y-3">
                           <a 
                             href={url} target="_blank" 
                             className="w-full flex items-center justify-center gap-2 py-3.5 bg-slate-900 text-white rounded-xl text-xs font-bold hover:bg-slate-800 transition-colors"
                           >
                              <Download className="w-4 h-4" /> Fonte Original
                           </a>
                           
                           <div className="space-y-2">
                             <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">Salvar em:</p>
                             <div className="grid grid-cols-1 gap-1.5">
                               {savedAreas.map(area => (
                                 <button 
                                   key={area}
                                   onClick={() => saveToArea(area)}
                                   className={cn(
                                     "flex items-center gap-2 p-2.5 rounded-xl text-xs font-semibold border transition-all",
                                     activeArea === area
                                       ? "border-green-200 bg-green-50 text-green-700"
                                       : "border-slate-100 hover:border-blue-200 hover:bg-blue-50 text-slate-600"
                                   )}
                                 >
                                   <Folder className="w-3.5 h-3.5" />
                                   {area}
                                   {isSaved && activeArea === area && <CheckCircle2 className="w-3.5 h-3.5 ml-auto text-green-500" />}
                                 </button>
                               ))}
                             </div>
                           </div>
                        </div>
                      </div>
                    </div>

                    {/* Content */}
                    <div className="lg:col-span-3 glass rounded-[3rem] p-10 md:p-16 shadow-2xl shadow-slate-200 bg-white border border-white">
                       <ReactMarkdown 
                         remarkPlugins={[remarkGfm]}
                         components={{
                            p: ({node, ...props}) => <p className="text-slate-700 leading-relaxed text-justify mb-8 text-[1.125rem] font-body" {...props} />,
                            strong: ({node, ...props}) => <strong className="font-black text-slate-900 bg-blue-50/80 px-1 rounded-sm border-b-2 border-blue-100" {...props} />,
                            h2: ({node, ...props}) => <h2 className="font-heading text-2xl md:text-3xl font-black mt-16 mb-8 text-slate-900 border-l-4 border-blue-600 pl-5 py-2" {...props} />,
                            h3: ({node, ...props}) => <h3 className="font-heading text-xl font-black mt-10 mb-5 text-blue-700" {...props} />,
                            ul: ({node, ...props}) => <ul className="space-y-4 my-8 pl-8 list-none" {...props} />,
                            li: ({node, ...props}) => (
                              <li className="relative pl-6 text-slate-700 leading-relaxed text-justify font-body text-lg">
                                <span className="absolute left-0 top-3 w-1.5 h-1.5 rounded-full bg-blue-500/40" />
                                {props.children}
                              </li>
                            ),
                            img: ({node, src, alt, ...props}) => {
                              // If R2 is configured, markdown already contains full URLs.
                              // Otherwise fall back to local backend serving.
                              const imgSrc = typeof src === "string" && src.startsWith("http")
                                ? src
                                : `${API_BASE}/api/outputs/${status.result.safe_name}/${src}`;
                              return (
                              <span className="block my-14 rounded-[2rem] overflow-hidden shadow-2xl ring-1 ring-slate-100 bg-white group/img">
                                 <img
                                   src={imgSrc}
                                   alt={alt}
                                   className="w-full h-auto object-cover group-hover/img:scale-105 transition-transform duration-1000"
                                   {...props}
                                 />
                                 {alt && <span className="block text-center text-sm font-bold text-slate-500 py-6 bg-slate-50/50 m-0 border-t border-slate-100 italic px-6 uppercase tracking-wider">{alt}</span>}
                              </span>
                              );
                            }
                         }}
                       >
                         {status.result.summary}
                       </ReactMarkdown>
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
