import { STUDENT_UPDATE } from '../data/placeholders'

export default function SCStudentUpdate() {
  const s = STUDENT_UPDATE

  return (
    <div className="sc-card" style={{ height: '100%' }}>
      <div className="sc-card-title">
        STUDENT UPDATE — {s.student_name}
      </div>

      <div className="sc-student-grid">
        <div className="sc-student-box">
          <div className="sc-student-box-label">Maths Score</div>
          <div className="sc-student-box-val">
            {s.maths_score}% <span className="arrow">↑</span>
          </div>
          <div className="sc-student-box-base">From {s.maths_baseline}% baseline</div>
        </div>

        <div className="sc-student-box">
          <div className="sc-student-box-label">Science Score</div>
          <div className="sc-student-box-val">
            {s.science_score}% <span className="arrow">↑</span>
          </div>
          <div className="sc-student-box-base">From {s.science_baseline}% baseline</div>
        </div>

        <div className="sc-student-box">
          <div className="sc-student-box-label">Attendance</div>
          <div className="sc-student-box-val">{s.attendance_pct}%</div>
          <div className="sc-student-box-base">This term</div>
        </div>

        <div className="sc-student-box">
          <div className="sc-student-box-label">Overall Improvement</div>
          <div className="sc-student-box-val">
            +{s.improvement_pts} pts <span className="arrow">↑</span>
          </div>
          <div className="sc-student-box-base">From personal baseline</div>
        </div>
      </div>

      <div className="sc-quote-box">
        School comment ({s.comment_date}): {s.school_comment}
      </div>
    </div>
  )
}
