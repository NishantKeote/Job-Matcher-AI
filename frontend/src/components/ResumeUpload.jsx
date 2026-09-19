import { useRef, useState } from 'react';
import ExperienceSelector from './ExperienceSelector';

const isPdf = (file) => file && (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf'));

export default function ResumeUpload({ experience, onExperienceChange, onSubmit, isLoading }) {
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const inputRef = useRef(null);
  const chooseFile = (candidate) => {
    if (!candidate) return;
    if (!isPdf(candidate)) { setFile(null); setError('Please choose a PDF resume.'); return; }
    setFile(candidate); setError('');
  };
  const handleDrop = (event) => { event.preventDefault(); chooseFile(event.dataTransfer.files?.[0]); };
  const handleSubmit = (event) => { event.preventDefault(); if (!file) { setError('Add your PDF resume before continuing.'); return; } onSubmit(file); };
  return <section className="upload-section" id="resume-upload">
    <div className="section-heading"><p className="eyebrow"><span /> START YOUR SEARCH</p><h2>A clearer path to your next role.</h2><p>We’ll read your resume and surface the roles that best fit your skills.</p></div>
    <form className="upload-panel" onSubmit={handleSubmit}>
      <label className="field-label">Where are you in your career?</label>
      <ExperienceSelector value={experience} onChange={onExperienceChange} />
      <label className="field-label" htmlFor="resume-file">Upload your resume</label>
      <div className={file ? 'drop-zone has-file' : 'drop-zone'} onDragOver={(event) => event.preventDefault()} onDrop={handleDrop} onClick={() => inputRef.current?.click()}>
        <input id="resume-file" ref={inputRef} type="file" accept="application/pdf,.pdf" onChange={(event) => chooseFile(event.target.files?.[0])} />
        <span className="upload-icon">↑</span>
        {file ? <><strong>{file.name}</strong><p>{(file.size / 1024 / 1024).toFixed(2)} MB · PDF ready</p><button type="button" className="text-button" onClick={(event) => { event.stopPropagation(); setFile(null); inputRef.current.value = ''; }}>Remove file</button></> : <><strong>Drop your resume here, or <u>browse</u></strong><p>PDF files only · Max file size depends on the service</p></>}
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="submit-button" type="submit" disabled={isLoading}>{isLoading ? <><span className="spinner" /> Finding your matches…</> : <>Get AI recommendations <span aria-hidden="true">→</span></>}</button>
      <p className="privacy-note">Your file is sent securely for recommendation processing.</p>
    </form>
  </section>;
}
