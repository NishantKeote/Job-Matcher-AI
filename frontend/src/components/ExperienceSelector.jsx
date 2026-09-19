const options = [
  { value: 'fresher', title: 'Fresher', caption: 'Starting your career' },
  { value: 'experienced', title: 'Experienced', caption: 'Growing your expertise' },
];

export default function ExperienceSelector({ value, onChange }) {
  return <div className="experience-selector" role="radiogroup" aria-label="Career stage">
    {options.map((option) => <button key={option.value} type="button" role="radio" aria-checked={value === option.value} className={value === option.value ? 'experience-option selected' : 'experience-option'} onClick={() => onChange(option.value)}>
      <span className="radio-dot" /><span><strong>{option.title}</strong><small>{option.caption}</small></span>
    </button>)}
  </div>;
}
