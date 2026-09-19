const fallbackSearch = (job) => {
  const parts = [job?.title, job?.company, job?.location].filter(Boolean).join(' ');
  return `https://www.naukri.com/jobs-in-india?k=${encodeURIComponent(parts)}`;
};

const scorePercent = (value) => Math.max(0, Math.min(100, Math.round((Number(value) || 0) * 100)));

export default function JobCard({ job, index }) {
  const title = job?.title || `Recommended role ${index + 1}`;
  const company = job?.company || 'Company not specified';
  const applicationUrl = job?.application_url || fallbackSearch(job);
  const direct = Boolean(job?.is_direct_application_url);
  const match = scorePercent(job?.match_score ?? job?.similarity_score);

  return <article className="job-card">
    <div className="job-card-top">
      <span className="job-number">{String(index + 1).padStart(2, '0')}</span>
      <span className="match-badge">✦ {match}% match</span>
    </div>

    <h3>{title}</h3>
    <p className="job-company">{company}</p>

    <div className="job-meta">
      {job?.location && <span>📍 {job.location}</span>}
      {job?.experience && <span>◷ {job.experience}</span>}
      {job?.salary && <span>₹ {job.salary.replace(/^₹\s*/, '')}</span>}
      {job?.posted && <span>◉ {job.posted}</span>}
    </div>

    <p>{job?.description || 'A role aligned with the experience and skills found in your resume.'}</p>

    <div className="match-breakdown">
      <span>Semantic {scorePercent(job?.similarity_score)}%</span>
      <span>Skills {scorePercent(job?.skill_score)}%</span>
      <span>Experience {scorePercent(job?.experience_score)}%</span>
    </div>

    <div className="job-actions">
      <a href={applicationUrl} target="_blank" rel="noopener noreferrer">
        {direct ? 'Open job listing' : 'Search current listing'} <span>↗</span>
      </a>
    </div>

    {!direct && <small className="listing-note">This older dataset entry does not contain its original posting URL, so we search using the job title, company and location.</small>}
  </article>;
}
