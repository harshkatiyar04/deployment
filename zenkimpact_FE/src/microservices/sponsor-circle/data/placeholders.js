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

export const LEADER_PROFILE = {
  name: 'Rohit Chawla',
  circle: 'Ashoka Rising Circle',
  initials: 'RC',
  role: 'Coordinator',
}

export const MEMBER_CONTRIBUTIONS = [
  { name: 'Rohit Chawla', initials: 'RC', role: 'Coordinator', totalContributed: 45000, thisMonth: 8000, pct: 36, badge: 'leader', zenq: 0.95 },
  { name: 'Priya Sharma', initials: 'PS', role: 'Sponsor Member', totalContributed: 28000, thisMonth: 8000, pct: 22, badge: '', zenq: 0.82 },
  { name: 'Arjun Kulkarni', initials: 'AK', role: 'Sponsor Member', totalContributed: 22000, thisMonth: 10000, pct: 18, badge: '', zenq: 0.78 },
  { name: 'Sneha Mehta', initials: 'SM', role: 'Mentor', totalContributed: 15500, thisMonth: 5000, pct: 12, badge: '', zenq: 0.71 },
  { name: 'Vikram Patil', initials: 'VP', role: 'CSR — TCS', totalContributed: 36000, thisMonth: 0, pct: 29, badge: 'csr', zenq: 0.60 },
  { name: 'Mrs. Devika', initials: 'MD', role: 'Guardian (Parent)', totalContributed: 4000, thisMonth: 0, pct: 3, badge: '', zenq: 0.45 },
]

export const TRANSACTION_HISTORY = [
  { date: '12 Mar', contributor: 'Arjun Kulkarni', type: 'Deposit', typeColor: '#dcfce7', amount: 10000 },
  { date: '28 Feb', contributor: 'TCS CSR Fund', type: 'CSR', typeColor: '#fef3c7', amount: 36000 },
  { date: '28 Feb', contributor: 'ICICI Bank', type: 'Interest', typeColor: '#e0e7ff', amount: 4000 },
  { date: '15 Feb', contributor: 'Priya Sharma', type: 'Deposit', typeColor: '#dcfce7', amount: 8000 },
  { date: '10 Feb', contributor: 'Rohit Chawla', type: 'Deposit', typeColor: '#dcfce7', amount: 15000 },
  { date: '01 Feb', contributor: 'Sneha Mehta', type: 'Deposit', typeColor: '#dcfce7', amount: 5000 },
]

export const VENDOR_PAYMENTS = [
  { id: 1, date: '10 Mar', vendor: 'ABC School — Term 2 Fees', amount: 42000, status: 'Paid', category: 'School Fees' },
  { id: 2, date: '05 Mar', vendor: 'Navneet Stationery Supplies', amount: 8200, status: 'Paid', category: 'Supplies' },
  { id: 3, date: '20 Feb', vendor: 'Pearson Edu — Textbooks', amount: 12500, status: 'Paid', category: 'Books' },
  { id: 4, date: '15 Feb', vendor: 'Uniform House', amount: 5500, status: 'Paid', category: 'Uniform' },
  { id: 5, date: '01 Apr', vendor: 'ABC School — Term 3 Fees', amount: 42000, status: 'Pending', category: 'School Fees' },
]

export const DM_MEMBERS = [
  { id: 'dm-ps', name: 'Priya Sharma', initials: 'PS', online: true },
  { id: 'dm-ak', name: 'Arjun Kulkarni', initials: 'AK', online: false },
  { id: 'dm-sm', name: 'Sneha Mehta', initials: 'SM', online: true },
  { id: 'dm-vp', name: 'Vikram Patil', initials: 'VP', online: false },
  { id: 'dm-md', name: 'Mrs. Devika', initials: 'MD', online: false },
]
