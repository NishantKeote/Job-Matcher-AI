export default function Hero() {
  return (
    <section className="hero" id="top">
      <div className="hero-copy">
        <p className="eyebrow"><span /> CAREER INTELLIGENCE, SIMPLIFIED</p>
        <h1>Your next great role is already in your <i>resume.</i></h1>
        <p className="hero-description">Upload your CV and let our AI turn your experience into a focused list of roles worth pursuing.</p>
        <a className="primary-button" href="#resume-upload">Analyze my resume <span aria-hidden="true">→</span></a>
        <div className="hero-proof">
          <div className="avatar-stack" aria-hidden="true"><b>AS</b><b>RK</b><b>MJ</b></div>
          <p><strong>Focused, practical matches</strong><br />Built around the skills you already have.</p>
        </div>
      </div>
      <div className="hero-art" aria-hidden="true">
        <div className="orb orb-one" /><div className="orb orb-two" />
        <div className="insight-card main-insight"><span className="spark">✦</span><p>AI role match</p><strong>92%</strong><small>Based on your profile</small><div className="meter"><span /></div></div>
        <div className="insight-card role-insight"><span className="mini-icon">⌘</span><div><small>TOP OPPORTUNITY</small><strong>Product Analyst</strong><p>Strong skills alignment</p></div><span className="arrow">↗</span></div>
        <div className="dot-grid" />
      </div>
    </section>
  );
}
