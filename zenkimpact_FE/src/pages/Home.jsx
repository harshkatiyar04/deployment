import Layout from '../components/Layout'
import {
  XMarkIcon,
  UserGroupIcon,
  LockClosedIcon,
  CurrencyDollarIcon,
  TrophyIcon,
  CheckCircleIcon,
  ArrowRightIcon
} from '@heroicons/react/24/outline'

function Home() {

  return (
    <Layout>
      <div className="space-y-0 -m-6">
        {/* Hero Section */}
        <section className="relative min-h-[90vh] flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-green-50 overflow-hidden">
          {/* Animated Background Elements */}
          <div className="absolute inset-0 overflow-hidden">
            <div className="absolute top-20 left-10 w-72 h-72 bg-blue-200 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-pulse"></div>
            <div className="absolute top-40 right-10 w-72 h-72 bg-green-200 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-pulse" style={{ animationDelay: '1s' }}></div>
            <div className="absolute -bottom-8 left-1/2 w-72 h-72 bg-purple-200 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-pulse" style={{ animationDelay: '2s' }}></div>
          </div>
          
          <div className="relative z-10 max-w-6xl mx-auto px-6 py-20 text-center">
            <h1 className="text-5xl md:text-7xl font-bold text-gray-900 mb-6">
              Transform a Child's Life
              <span className="block text-blue-600 mt-2">One Contribution at a Time</span>
            </h1>
            <p className="text-xl md:text-2xl text-gray-700 mb-8 max-w-3xl mx-auto">
              From passive donation to <strong>active digital adoption</strong>. 
              See your impact, measure your contribution, and watch dreams become reality.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <button className="px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-lg transform transition hover:scale-105">
                Start Your Impact Journey
              </button>
              <button className="px-8 py-4 bg-white hover:bg-gray-50 text-gray-700 font-semibold rounded-xl shadow-md border border-gray-200 transform transition hover:scale-105">
                Learn How It Works
              </button>
            </div>
          </div>
        </section>

        {/* The Problem Section */}
        <section className="py-20 bg-white">
          <div className="max-w-6xl mx-auto px-6">
            <div className="text-center mb-16">
              <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
                The Impulse to Give is Universal.<br/>
                <span className="text-red-600">The Path to Impact is Broken.</span>
              </h2>
              <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                Millions want to support a child's education. They want to mentor, guide, and see the direct result of their contributions. Yet, current systems are often opaque, distant, and unengaging.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              <div className="p-8 rounded-xl bg-red-50 border-2 border-red-200 transform transition hover:scale-105">
                <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
                  <XMarkIcon className="w-8 h-8 text-red-600" />
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-3">Disconnected</h3>
                <p className="text-gray-700">Sponsors are detached from the real, day-to-day impact of their contributions. The human element is lost.</p>
              </div>

              <div className="p-8 rounded-xl bg-orange-50 border-2 border-orange-200 transform transition hover:scale-105">
                <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center mb-4">
                  <UserGroupIcon className="w-8 h-8 text-orange-600" />
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-3">Impersonal</h3>
                <p className="text-gray-700">The focus is solely on financial transactions, missing the crucial value of mentorship, guidance, and encouragement.</p>
              </div>

              <div className="p-8 rounded-xl bg-yellow-50 border-2 border-yellow-200 transform transition hover:scale-105">
                <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mb-4">
                  <LockClosedIcon className="w-8 h-8 text-yellow-600" />
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-3">Opaque</h3>
                <p className="text-gray-700">There is little to no transparency on how funds are used. Accountability is a constant concern.</p>
              </div>
            </div>
          </div>
        </section>

        {/* The ZenK Solution - Transformation */}
        <section className="py-20 bg-gradient-to-br from-blue-50 to-green-50">
          <div className="max-w-6xl mx-auto px-6">
            <div className="text-center mb-16">
              <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
                The ZenK Way:<br/>
                <span className="text-blue-600">From Passive Donation to Active Digital Adoption</span>
              </h2>
              <p className="text-xl text-gray-700 max-w-3xl mx-auto">
                We transform sponsorship into an active partnership where every contribution creates measurable impact with zero misuse.
              </p>
            </div>

            {/* Comparison Table */}
            <div className="rounded-xl bg-white shadow-sm border border-gray-200 overflow-hidden mb-12">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">The Old Way</th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-blue-600">The ZenK Way</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    <tr className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-gray-600">Donation</td>
                      <td className="px-6 py-4 text-gray-900 font-semibold">Sponsor Circle</td>
                    </tr>
                    <tr className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-gray-600">Sponsor → Organisation → Student</td>
                      <td className="px-6 py-4 text-gray-900 font-semibold">Active Partnership</td>
                    </tr>
                    <tr className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-gray-600">Disconnected & Impersonal</td>
                      <td className="px-6 py-4 text-gray-900 font-semibold">Connected & Engaging</td>
                    </tr>
                    <tr className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-gray-600">Opaque Financial Flow</td>
                      <td className="px-6 py-4 text-gray-900 font-semibold">Complete Transparency</td>
                    </tr>
                    <tr className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-gray-600">Single Sponsor</td>
                      <td className="px-6 py-4 text-gray-900 font-semibold">Collaborative Sponsor Circles</td>
                    </tr>
                    <tr className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-gray-600">No Measurable Impact</td>
                      <td className="px-6 py-4 text-gray-900 font-semibold">Gamified Impact League</td>
                    </tr>
                    <tr className="hover:bg-gray-50 bg-green-50">
                      <td className="px-6 py-4 text-gray-600">Passive Contribution</td>
                      <td className="px-6 py-4 text-green-700 font-bold text-lg">Active Digital Adoption</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </section>

        {/* Three Pillars Section */}
        <section className="py-20 bg-white">
          <div className="max-w-6xl mx-auto px-6">
            <div className="text-center mb-16">
              <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
                Three Pillars for<br/>
                <span className="text-blue-600">Holistic Support</span>
              </h2>
              <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                ZenK combines mentoring, tutoring, and financial assistance with measurable engagement and gamified group participation.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              {/* Pillar 1: Human Support */}
              <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-8 transform transition hover:scale-105 hover:shadow-lg">
                <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mb-6 mx-auto">
                  <UserGroupIcon className="w-10 h-10 text-blue-600" />
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-4 text-center">Pillar 1: Human Support</h3>
                <p className="text-lg text-gray-700 mb-4 text-center font-semibold">Direct investment of time and wisdom</p>
                <ul className="space-y-3 text-gray-600">
                  <li className="flex items-start">
                    <CheckCircleIcon className="w-5 h-5 text-green-500 mr-2 mt-1 flex-shrink-0" />
                    <span>Learning guidance & mentorship</span>
                  </li>
                  <li className="flex items-start">
                    <CheckCircleIcon className="w-5 h-5 text-green-500 mr-2 mt-1 flex-shrink-0" />
                    <span>Life-skills coaching</span>
                  </li>
                  <li className="flex items-start">
                    <CheckCircleIcon className="w-5 h-5 text-green-500 mr-2 mt-1 flex-shrink-0" />
                    <span>Consistent encouragement</span>
                  </li>
                </ul>
              </div>

              {/* Pillar 2: Financial Support */}
              <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-8 transform transition hover:scale-105 hover:shadow-lg">
                <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mb-6 mx-auto">
                  <CurrencyDollarIcon className="w-10 h-10 text-green-600" />
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-4 text-center">Pillar 2: Financial Support</h3>
                <p className="text-lg text-gray-700 mb-4 text-center font-semibold">100% accountable funding</p>
                <ul className="space-y-3 text-gray-600">
                  <li className="flex items-start">
                    <CheckCircleIcon className="w-5 h-5 text-green-500 mr-2 mt-1 flex-shrink-0" />
                    <span>Tuition support</span>
                  </li>
                  <li className="flex items-start">
                    <CheckCircleIcon className="w-5 h-5 text-green-500 mr-2 mt-1 flex-shrink-0" />
                    <span>Books & devices</span>
                  </li>
                  <li className="flex items-start">
                    <CheckCircleIcon className="w-5 h-5 text-green-500 mr-2 mt-1 flex-shrink-0" />
                    <span>Skill-building programs</span>
                  </li>
                  <li className="flex items-start">
                    <CheckCircleIcon className="w-5 h-5 text-green-500 mr-2 mt-1 flex-shrink-0" />
                    <span><strong>Zero misuse</strong> - closed-loop system</span>
                  </li>
                </ul>
              </div>

              {/* Pillar 3: Gamification */}
              <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-8 transform transition hover:scale-105 hover:shadow-lg">
                <div className="w-20 h-20 bg-purple-100 rounded-full flex items-center justify-center mb-6 mx-auto">
                  <TrophyIcon className="w-10 h-10 text-purple-600" />
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-4 text-center">Pillar 3: Gamification</h3>
                <p className="text-lg text-gray-700 mb-4 text-center font-semibold">Making impact social and rewarding</p>
                <ul className="space-y-3 text-gray-600">
                  <li className="flex items-start">
                    <CheckCircleIcon className="w-5 h-5 text-green-500 mr-2 mt-1 flex-shrink-0" />
                    <span>Impact League leaderboards</span>
                  </li>
                  <li className="flex items-start">
                    <CheckCircleIcon className="w-5 h-5 text-green-500 mr-2 mt-1 flex-shrink-0" />
                    <span>Sponsor Circles competition</span>
                  </li>
                  <li className="flex items-start">
                    <CheckCircleIcon className="w-5 h-5 text-green-500 mr-2 mt-1 flex-shrink-0" />
                    <span>Impact Missions & badges</span>
                  </li>
                  <li className="flex items-start">
                    <CheckCircleIcon className="w-5 h-5 text-green-500 mr-2 mt-1 flex-shrink-0" />
                    <span>Real-time impact scoring</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* Impact League Section */}
        <section className="py-20 bg-gradient-to-br from-purple-50 to-blue-50">
          <div className="max-w-6xl mx-auto px-6">
            <div className="text-center mb-16">
              <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
                The Impact League:<br/>
                <span className="text-purple-600">Where Your Impact Becomes Visible</span>
              </h2>
              <p className="text-xl text-gray-700 max-w-3xl mx-auto">
                Transform sponsorship into a competitive, collaborative experience that motivates deeper engagement and celebrates results.
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-8 mb-12">
              <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-8">
                <h3 className="text-2xl font-bold text-gray-900 mb-4">How It Works</h3>
                <ul className="space-y-4 text-gray-700">
                  <li className="flex items-start">
                    <span className="flex-shrink-0 w-8 h-8 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center font-bold mr-3">1</span>
                    <div>
                      <strong className="text-gray-900">Form Sponsor Circles</strong>
                      <p className="text-sm text-gray-600">Join or create circles with other sponsors to collectively support learners</p>
                    </div>
                  </li>
                  <li className="flex items-start">
                    <span className="flex-shrink-0 w-8 h-8 bg-green-100 text-green-600 rounded-full flex items-center justify-center font-bold mr-3">2</span>
                    <div>
                      <strong className="text-gray-900">Earn Impact Scores</strong>
                      <p className="text-sm text-gray-600">Score points through mentoring time, quality, student improvements, and financial support</p>
                    </div>
                  </li>
                  <li className="flex items-start">
                    <span className="flex-shrink-0 w-8 h-8 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center font-bold mr-3">3</span>
                    <div>
                      <strong className="text-gray-900">Complete Impact Missions</strong>
                      <p className="text-sm text-gray-600">Take on targeted challenges like funding specific courses for bonus recognition</p>
                    </div>
                  </li>
                  <li className="flex items-start">
                    <span className="flex-shrink-0 w-8 h-8 bg-yellow-100 text-yellow-600 rounded-full flex items-center justify-center font-bold mr-3">4</span>
                    <div>
                      <strong className="text-gray-900">Climb the Leaderboard</strong>
                      <p className="text-sm text-gray-600">See how your circle ranks and earn badges for your contributions</p>
                    </div>
                  </li>
                </ul>
              </div>

              <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-8">
                <h3 className="text-2xl font-bold text-gray-900 mb-6">Example Leaderboard</h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-gradient-to-r from-yellow-50 to-yellow-100 rounded-lg border-2 border-yellow-300">
                    <div className="flex items-center">
                      <span className="text-2xl font-bold text-yellow-600 mr-4">🥇</span>
                      <div>
                        <div className="font-bold text-gray-900">The Navigators</div>
                        <div className="text-sm text-gray-600">Impact Score: 12,450</div>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg border border-gray-300">
                    <div className="flex items-center">
                      <span className="text-2xl font-bold text-gray-500 mr-4">🥈</span>
                      <div>
                        <div className="font-bold text-gray-900">The Catalysts</div>
                        <div className="text-sm text-gray-600">Impact Score: 10,890</div>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-gradient-to-r from-orange-50 to-orange-100 rounded-lg border border-orange-300">
                    <div className="flex items-center">
                      <span className="text-2xl font-bold text-orange-600 mr-4">🥉</span>
                      <div>
                        <div className="font-bold text-gray-900">The Vanguard</div>
                        <div className="text-sm text-gray-600">Impact Score: 9,210</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Impact Story Section */}
        <section className="py-20 bg-white">
          <div className="max-w-6xl mx-auto px-6">
            <div className="text-center mb-16">
              <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
                Your Contribution,<br/>
                <span className="text-green-600">Their Transformation</span>
              </h2>
              <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                Every pound creates measurable impact. Every hour of mentoring shapes a future. Every contribution matters.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              <div className="text-center p-8 rounded-xl bg-blue-50 border-2 border-blue-200">
                <div className="text-5xl font-bold text-blue-600 mb-2">100%</div>
                <div className="text-xl font-semibold text-gray-900 mb-2">Transparency</div>
                <p className="text-gray-700">Every contribution is tracked from start to finish. Zero misuse guaranteed.</p>
              </div>

              <div className="text-center p-8 rounded-xl bg-green-50 border-2 border-green-200">
                <div className="text-5xl font-bold text-green-600 mb-2">24/7</div>
                <div className="text-xl font-semibold text-gray-900 mb-2">Visibility</div>
                <p className="text-gray-700">See real-time progress, impact scores, and student achievements as they happen.</p>
              </div>

              <div className="text-center p-8 rounded-xl bg-purple-50 border-2 border-purple-200">
                <div className="text-5xl font-bold text-purple-600 mb-2">∞</div>
                <div className="text-xl font-semibold text-gray-900 mb-2">Impact</div>
                <p className="text-gray-700">Your support doesn't just help one child—it transforms families and communities.</p>
              </div>
            </div>
          </div>
        </section>

        {/* Call to Action Section */}
        <section className="py-20 bg-gradient-to-br from-blue-600 to-purple-600 text-white">
          <div className="max-w-4xl mx-auto px-6 text-center">
            <h2 className="text-4xl md:text-5xl font-bold mb-6">
              Ready to Make a Difference?
            </h2>
            <p className="text-xl mb-8 text-blue-100">
              Join thousands of sponsors who are transforming children's lives through active digital adoption. 
              Start your impact journey today.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button className="px-8 py-4 bg-white text-blue-600 font-semibold rounded-xl shadow-lg transform transition hover:scale-105 hover:bg-gray-50 flex items-center justify-center gap-2">
                Create Your Sponsor Circle
                <ArrowRightIcon className="w-5 h-5" />
              </button>
              <button className="px-8 py-4 bg-transparent border-2 border-white text-white font-semibold rounded-xl transform transition hover:scale-105 hover:bg-white hover:text-blue-600 flex items-center justify-center gap-2">
                Explore Impact Missions
                <ArrowRightIcon className="w-5 h-5" />
              </button>
            </div>
          </div>
        </section>

        {/* Footer Note */}
        <footer className="py-12 bg-gray-900 text-gray-400 text-center">
          <p className="text-lg mb-2">The World's Most Trusted Digital Sponsorship Ecosystem</p>
          <p className="text-sm">Enabling millions of sponsors to contribute meaningfully — with joy, accountability, and transparency.</p>
        </footer>
      </div>
    </Layout>
  )
}

export default Home

