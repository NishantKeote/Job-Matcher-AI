import { useState } from 'react';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import ResumeUpload from './components/ResumeUpload';
import JobResults from './components/JobResults';
import Footer from './components/Footer';
import { uploadResume } from './services/api';

export default function App() {
  const [experience, setExperience] = useState('fresher');
  const [jobs, setJobs] = useState([]);
  const [liveJobs, setLiveJobs] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState('');
  const handleUpload = async (file) => {
    setIsLoading(true); setApiError(''); setJobs([]); setLiveJobs(false);
    try { const result = await uploadResume(file, experience); setJobs(result.jobs); setLiveJobs(result.liveJobs); }
    catch (error) { setApiError(error.message || 'Something went wrong while finding your recommendations.'); }
    finally { setIsLoading(false); }
  };
  return <><Navbar /><main><Hero /><ResumeUpload experience={experience} onExperienceChange={setExperience} onSubmit={handleUpload} isLoading={isLoading} />{apiError && <p className="api-error" role="alert">{apiError}</p>}{isLoading && <section className="loading-state" aria-live="polite"><span className="loading-orbit"><i /></span><div><p className="eyebrow"><span /> AI ANALYSIS IN PROGRESS</p><h2>Reading the story in your resume…</h2><p>We’re identifying roles that put your skills to work.</p></div></section>}<JobResults jobs={jobs} experience={experience} liveJobs={liveJobs} /></main><Footer /></>;
}
