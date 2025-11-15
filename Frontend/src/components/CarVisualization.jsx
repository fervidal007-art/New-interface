import { Car } from 'lucide-react';

function CarVisualization() {
  return (
    <div className="car-visualization">
      {/* Car in center */}
      <div className="car-icon">
        <Car size={80} strokeWidth={1.5} />
      </div>


      {/* Grid lines */}
      <div className="grid-overlay">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="grid-line" style={{ left: `${i * 12.5}%` }}></div>
        ))}
      </div>
    </div>
  );
}

export default CarVisualization;

