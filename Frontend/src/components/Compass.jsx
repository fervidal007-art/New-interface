import { Navigation } from 'lucide-react';

function Compass({ direction = 0 }) {
  return (
    <div className="compass">
      <div className="compass-directions">
        <span className="dir-n">N</span>
        <span className="dir-e">E</span>
        <span className="dir-s">S</span>
        <span className="dir-w">W</span>
      </div>
      <div className="compass-needle" style={{ transform: `rotate(${direction}deg)` }}>
        <Navigation size={24} />
      </div>
    </div>
  );
}

export default Compass;

