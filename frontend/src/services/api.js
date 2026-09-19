const apiBaseUrl = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001').replace(/\/$/, '');

export async function uploadResume(file, experience = 'fresher') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('experience', experience);

  let response;
  try {
    response = await fetch(`${apiBaseUrl}/upload_resume`, {
      method: 'POST',
      body: formData,
    });
  } catch {
    throw new Error('We could not reach the recommendation service. Check your connection and try again.');
  }

  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error('The recommendation service returned an unexpected response.');
  }

  if (!response.ok) {
    if (response.status >= 500) {
      throw new Error(data?.detail || 'The recommendation service is temporarily unavailable.');
    }
    throw new Error(data?.detail || data?.message || 'Your resume could not be processed. Please try again.');
  }

  if (!Array.isArray(data?.jobs)) {
    throw new Error('The recommendation service returned an invalid jobs response.');
  }

  return { jobs: data.jobs, liveJobs: Boolean(data.live_jobs), jobCount: Number(data.job_count || data.jobs.length) };
}
