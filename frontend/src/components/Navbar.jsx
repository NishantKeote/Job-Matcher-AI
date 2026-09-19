export default function Navbar() {
  return (
    <nav className="navbar" aria-label="Main navigation">
      <a className="brand" href="#top" aria-label="JobMatcher AI home">
        {/* <span className="brand-mark">J</span> */}
        <span>Job Matcher <em>AI</em></span>
      </a>
      <a className="nav-cta" href="#resume-upload">Get matched <span aria-hidden="true">↗</span></a>
    </nav>
  );
}
