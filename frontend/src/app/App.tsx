import { Activity, ArrowUpRight, BarChart3, BrainCircuit, Database, Layers3, Sparkles } from "lucide-react";

const features = [
  { icon: Database, title: "Automated Data Analytics", detail: "Prepare the foundation for profiling, cleaning, and exploratory analysis." },
  { icon: BarChart3, title: "Interactive Visualization Studio", detail: "Build a workspace for multiple editable charts and dashboard layouts." },
  { icon: BrainCircuit, title: "Business Decision Intelligence", detail: "Connect verified analytics, forecasting, and what-if scenario tools." },
];

export default function App() {
  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand-mark"><Layers3 size={21} /></div>
        <div className="brand-copy"><strong>Analyticx AI</strong><span>ANALYTICS WORKSPACE</span></div>
        <div className="nav-label">WORKSPACE</div>
        <div className="nav-item active"><Activity size={17} /> Overview</div>
        <div className="nav-item"><Database size={17} /> Data Explorer</div>
        <div className="nav-item"><BarChart3 size={17} /> Visualization Studio</div>
        <div className="nav-item"><BrainCircuit size={17} /> Decision Intelligence</div>
        <div className="sidebar-bottom">Local development scaffold<br /><span>Features are added phase by phase.</span></div>
      </aside>
      <section className="main-content">
        <header className="topbar"><div><span className="eyebrow">BUSINESS INTELLIGENCE / OVERVIEW</span><h1>Turn data into decisions.</h1></div><div className="local-pill"><span className="status-dot" /> Local workspace</div></header>
        <section className="hero-panel"><div className="hero-orb orb-one"/><div className="hero-orb orb-two"/><div className="hero-content"><div className="pill"><Sparkles size={14}/> AGENTIC BUSINESS ANALYTICS</div><h2>Your data-to-decision<br/><em>workspace starts here.</em></h2><p>This starter interface is ready for the next implementation phase: real dataset upload, automated EDA, interactive charts, and local LLM integration.</p><button className="primary-button" onClick={() => alert("Upload workflow is not implemented in this scaffold yet.")}>Explore workspace <ArrowUpRight size={16}/></button></div><div className="hero-visual"><div className="visual-ring ring-a"/><div className="visual-ring ring-b"/><div className="visual-core"><BrainCircuit size={42}/></div><div className="float-tag tag-top"><Activity size={14}/> Analytics engine</div><div className="float-tag tag-bottom"><Database size={14}/> Data workspace</div></div></section>
        <div className="section-heading"><div><span className="eyebrow">PLATFORM MODULES</span><h3>Build your analytics workflow</h3></div><span className="scaffold-tag">Starter UI · Not full implementation</span></div>
        <div className="feature-grid">{features.map(({icon: Icon, title, detail}, index) => <article className="feature-card" key={title}><div className={`feature-icon feature-${index}`}><Icon size={20}/></div><h4>{title}</h4><p>{detail}</p><div className="card-footer"><span>Planned module</span><ArrowUpRight size={15}/></div></article>)}</div>
        <footer className="footer-note">ANALYTICX AI <span>•</span> Local project scaffold <span>•</span> No external LLM API configured</footer>
      </section>
    </main>
  );
}
