import JobCard from './JobCard';

export default function JobResults({ jobs, experience, liveJobs }) {
  if (!jobs.length) return null;
  const shownJobs = jobs.slice(0, 10);
  return <section className="results-section" id="recommendations"><div className="results-intro"><div><p className="eyebrow"><span /> YOUR PERSONALIZED RESULTS</p><h2>Roles matched to your momentum.</h2></div><p>{liveJobs ? 'Showing current listings fetched from the live job provider.' : 'Showing recommendations from the local job dataset.'}</p></div><div className="jobs-grid">{shownJobs.map((job, index) => <JobCard key={`${job?.title || 'role'}-${index}`} job={job} index={index} experience={experience} />)}</div></section>;
}
