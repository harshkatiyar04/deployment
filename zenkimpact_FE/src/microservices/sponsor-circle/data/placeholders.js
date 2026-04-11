export const SUMMARY = {
  zenq_score: 82,
  circle_rank: 3,
  total_circles: 47,
  participation_pct: 74,
  circle_avg_pct: 68,
  time_this_month_hrs: 6.5,
  top_group_hrs: 11.2,
  zenq_change: 4,
  rank_previous: 5,
}

export const BUDGET = {
  total_budget: 150000,
  spent: 94200,
  collected: 124500,
  balance_to_spend: 55800,
  fy_label: 'FY 2025–26',
  transactions: [
    { date: 'Mar 20', description: 'New Member Kit', amount: 5000, category: 'Operational' },
    { date: 'Mar 15', description: 'Kia AI Tokens', amount: 3500, category: 'Platform' },
    { date: 'Mar 10', description: 'School Supplies', amount: 12000, category: 'Student' },
  ],
}

export const PARTICIPATION = {
  members: [
    { name: 'Rohit Chawla', initials: 'RC', participation_pct: 94, badge: 'top' },
    { name: 'Harsh Katiyar', initials: 'HK', participation_pct: 74, badge: 'you' },
    { name: 'Arjun Kulkarni', initials: 'AK', participation_pct: 70, badge: '' },
    { name: 'Sneha Mehta', initials: 'SM', participation_pct: 64, badge: '' },
    { name: 'Vikram Patil', initials: 'VP', participation_pct: 60, badge: '' },
    { name: 'Mrs. Devika', initials: 'MD', participation_pct: 46, badge: '' },
  ],
  circle_avg_pct: 68,
  leader_name: 'Rohit Chawla',
  leader_pct: 94,
}

export const STUDENT_UPDATE = {
  student_name: 'Ananya D.',
  maths_score: 84,
  maths_baseline: 61,
  science_score: 78,
  science_baseline: 55,
  attendance_pct: 92,
  improvement_pts: 23,
  school_comment:
    'Ananya is asking about entering a district-level science competition. Excellent engagement this term.',
  comment_date: '8 Mar',
}

export const TIME_IMPACT = {
  total_hrs_all_circles: 847,
  total_circles_count: 47,
  highest_circle_hrs: 11.2,
  highest_circle_name: 'Vasundhara Circle, Pune',
  my_circle_hrs: 6.5,
}

export const RANKINGS = [
  { rank: 1, name: 'Vasundhara Circle', zenq: 96, city: 'Pune', is_mine: false },
  { rank: 2, name: 'Prarambh Mumbai', zenq: 89, city: 'Mumbai', is_mine: false },
  { rank: 3, name: 'VIT Rising', zenq: 82, city: 'Mumbai', is_mine: true },
  { rank: 4, name: 'Udaan Bangalore', zenq: 78, city: 'Bengaluru', is_mine: false },
  { rank: 5, name: 'Kishore Circle', zenq: 71, city: 'Delhi', is_mine: false },
]

export const USER_PROFILE = {
  name: 'Harsh Katiyar',
  circle: 'VIT Rising Circle',
  initials: 'HK',
}
