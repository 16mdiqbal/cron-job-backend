# Frontend Architecture - Cron Job Management System

## Table of Contents
1. [Overview](#overview)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Development Phases](#development-phases)
5. [Implementation Details](#implementation-details)
6. [Integration Points](#integration-points)
7. [Testing Strategy](#testing-strategy)
8. [Deployment](#deployment)
9. [Git Workflow](#git-workflow)
10. [Development Checklist](#development-checklist)

---

## Overview

This document outlines the comprehensive architecture for building the frontend UI for the Cron Job Management System. The frontend will provide a complete user interface for job management, authentication, monitoring, and reporting.

### Key Objectives
- **User-Friendly Dashboard**: Real-time visualization of scheduled jobs and execution history
- **Secure Authentication**: JWT-based login with role-based access control
- **Job Management**: Create, edit, delete, and monitor cron jobs
- **Execution Tracking**: View detailed execution history and statistics
- **Email Notifications**: Configure and manage notification preferences
- **Performance Analytics**: Charts and statistics for job performance
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile devices

### Target Users
- **Admin**: Full system access, user management, system configuration
- **User**: Create and manage their own jobs, view executions
- **Viewer**: Read-only access to jobs and execution history

---

## Technology Stack

### Core Framework
- **React 18** - Latest version with concurrent rendering and automatic batching
  - Why: Industry standard, excellent component ecosystem, optimal performance
  - Version: 18.3+
  - Features: Hooks, Suspense, Server Components support

- **TypeScript** - Static type checking for safer code
  - Why: Catches bugs at compile time, better IDE support, self-documenting code
  - Configuration: Strict mode enabled
  - tsconfig.json with target ES2020

### Build & Dev Server
- **Vite** - Next-generation frontend build tool
  - Why: 10-30x faster than Webpack, instant HMR, optimized build output
  - Version: 5.0+
  - Plugins: @vitejs/plugin-react, @vitejs/plugin-react-swc (for faster builds)

### Styling
- **Tailwind CSS** - Utility-first CSS framework
  - Why: Consistent design system, rapid development, small bundle size
  - Version: 3.4+
  - Configuration: Dark mode support, custom theme colors
  - PostCSS: Automated vendor prefixing

- **shadcn/ui** - Pre-built accessible components
  - Why: Built on Radix UI (accessible), Tailwind styled, tree-shakeable
  - Components: Button, Input, Card, Dialog, Table, Select, etc.
  - Customizable via design system

### State Management
- **Zustand** - Lightweight state management
  - Why: 70 LOC vs 700 with Redux, no boilerplate, TypeScript-friendly
  - Stores:
    - `authStore` - User authentication, tokens, roles
    - `jobStore` - Job list, filters, pagination
    - `uiStore` - UI state, modals, notifications
    - `executionStore` - Execution history, sorting
  - DevTools: Redux DevTools integration

### HTTP Client
- **Axios** - Promise-based HTTP client
  - Why: Request/response interceptors, automatic retries, timeout handling
  - Version: 1.6+
  - Features:
    - Request interceptor for JWT token injection
    - Response interceptor for error handling
    - Retry logic for failed requests
    - Request/response transformers

### Routing
- **React Router v6** - Client-side routing
  - Why: Built-in data loading, error boundaries, code splitting
  - Features:
    - Nested route configuration
    - Protected routes for authentication
    - Lazy loading with Suspense
    - Programmatic navigation

### Forms
- **React Hook Form** - Performant form management
  - Why: Minimal re-renders, easy validation, small bundle size
  - Integration: Tailwind + shadcn/ui components
  - Features: Controller pattern, custom validation, async validation

### Charts & Visualization
- **Recharts** - React charting library
  - Why: React-first, responsive, accessible, interactive
  - Components: LineChart, BarChart, PieChart, AreaChart
  - Features: Tooltips, Legends, Custom shapes

### Testing
- **Vitest** - Unit and integration testing
  - Why: Vite-native, Jest-compatible API, instant HMR
  - Configuration: Coverage reports, watch mode

- **React Testing Library** - Component testing
  - Why: Tests behavior, not implementation; encourages good practices
  - Features: User-centric queries, async utilities

- **Playwright** - E2E testing (Phase 9)
  - Why: Cross-browser support, visual regression testing
  - Components: Authentication flow, critical paths

### Development Tools
- **ESLint** - Code quality
  - Config: airbnb-typescript-prettier rules
  
- **Prettier** - Code formatting
  - Config: 2-space indentation, single quotes

- **Husky** - Git hooks
  - Pre-commit: ESLint, format check
  - Pre-push: Run tests

- **pnpm** - Package manager
  - Why: Faster, more disk-efficient, monorepo-ready

---

## Project Structure

```
cron-job-frontend/
├── .husky/                          # Git hooks
│   ├── pre-commit
│   └── pre-push
├── .vscode/
│   └── settings.json                # VSCode configuration for Prettier, ESLint
├── public/
│   ├── favicon.ico
│   ├── logo.svg
│   └── manifest.json
├── src/
│   ├── assets/
│   │   ├── images/
│   │   │   ├── logo.svg
│   │   │   ├── logo-dark.svg
│   │   │   ├── empty-state.svg
│   │   │   └── error-illustration.svg
│   │   ├── icons/
│   │   │   └── index.ts              # Icon exports
│   │   └── styles/
│   │       ├── globals.css           # Global styles
│   │       └── animations.css        # Custom animations
│   │
│   ├── components/
│   │   ├── auth/
│   │   │   ├── LoginForm.tsx         # Login component
│   │   │   ├── LogoutButton.tsx      # Logout component
│   │   │   └── ProtectedRoute.tsx    # Route protection
│   │   │
│   │   ├── layout/
│   │   │   ├── Header.tsx            # Top navigation
│   │   │   ├── Sidebar.tsx           # Left sidebar
│   │   │   ├── Layout.tsx            # Main layout wrapper
│   │   │   ├── Footer.tsx            # Footer (optional)
│   │   │   └── Breadcrumb.tsx        # Breadcrumb navigation
│   │   │
│   │   ├── jobs/
│   │   │   ├── JobList.tsx           # List view
│   │   │   ├── JobCard.tsx           # Individual job card
│   │   │   ├── JobForm.tsx           # Create/Edit form
│   │   │   ├── JobDetail.tsx         # Detailed view
│   │   │   ├── CronExpressionHelper.tsx # Cron expression builder
│   │   │   ├── JobFilters.tsx        # Filter controls
│   │   │   ├── JobPagination.tsx     # Pagination
│   │   │   └── BulkActions.tsx       # Bulk operations
│   │   │
│   │   ├── executions/
│   │   │   ├── ExecutionList.tsx     # Execution history
│   │   │   ├── ExecutionDetail.tsx   # Execution details
│   │   │   ├── ExecutionStats.tsx    # Statistics panel
│   │   │   ├── ExecutionCharts.tsx   # Performance charts
│   │   │   └── ExecutionFilters.tsx  # Filter controls
│   │   │
│   │   ├── notifications/
│   │   │   ├── NotificationSettings.tsx # Settings page
│   │   │   ├── NotificationToggle.tsx # Enable/disable toggle
│   │   │   ├── NotificationForm.tsx  # Configuration form
│   │   │   └── NotificationPreview.tsx # Email preview
│   │   │
│   │   ├── users/
│   │   │   ├── UserList.tsx          # User management (Admin)
│   │   │   ├── UserForm.tsx          # Create/Edit user
│   │   │   ├── UserDetail.tsx        # User profile
│   │   │   ├── RoleManager.tsx       # Role assignment
│   │   │   └── PermissionMatrix.tsx  # Permission visualization
│   │   │
│   │   ├── common/
│   │   │   ├── Button.tsx            # Custom button wrapper
│   │   │   ├── Card.tsx              # Card wrapper
│   │   │   ├── Modal.tsx             # Modal dialog
│   │   │   ├── LoadingSpinner.tsx    # Loading state
│   │   │   ├── EmptyState.tsx        # Empty state
│   │   │   ├── ErrorBoundary.tsx     # Error boundary
│   │   │   ├── Toast.tsx             # Toast notifications
│   │   │   ├── ConfirmDialog.tsx     # Confirmation dialog
│   │   │   ├── Badge.tsx             # Status badge
│   │   │   └── StatusIndicator.tsx   # Online/offline indicator
│   │   │
│   │   ├── dashboard/
│   │   │   ├── Dashboard.tsx         # Main dashboard
│   │   │   ├── StatsCard.tsx         # Statistics card
│   │   │   ├── RecentJobs.tsx        # Recent jobs widget
│   │   │   ├── ExecutionTrend.tsx    # Trend chart
│   │   │   └── HealthStatus.tsx      # System health
│   │   │
│   │   └── settings/
│   │       ├── SettingsLayout.tsx    # Settings wrapper
│   │       ├── ProfileSettings.tsx   # User profile
│   │       ├── SecuritySettings.tsx  # Password, 2FA
│   │       └── SystemSettings.tsx    # Admin settings
│   │
│   ├── hooks/
│   │   ├── useAuth.ts                # Authentication hook
│   │   ├── useJobs.ts                # Jobs CRUD hook
│   │   ├── useExecutions.ts          # Execution history hook
│   │   ├── usePagination.ts          # Pagination logic
│   │   ├── useLocalStorage.ts        # Local storage sync
│   │   ├── useDebounce.ts            # Debounce hook
│   │   ├── useAsync.ts               # Async data loading
│   │   ├── useNotification.ts        # Toast notifications
│   │   ├── useQueryParams.ts         # URL query params
│   │   └── usePolling.ts             # Auto-refresh data
│   │
│   ├── services/
│   │   ├── api/
│   │   │   ├── client.ts             # Axios instance with interceptors
│   │   │   ├── authService.ts        # Authentication API
│   │   │   ├── jobService.ts         # Jobs API
│   │   │   ├── executionService.ts   # Executions API
│   │   │   ├── userService.ts        # Users API
│   │   │   ├── notificationService.ts # Notifications API
│   │   │   ├── healthService.ts      # Health checks
│   │   │   └── errorHandler.ts       # Centralized error handling
│   │   │
│   │   ├── storage/
│   │   │   ├── tokenStorage.ts       # JWT token persistence
│   │   │   ├── userPreferences.ts    # User preferences (theme, etc.)
│   │   │   └── cacheManager.ts       # Response caching
│   │   │
│   │   └── utils/
│   │       ├── formatters.ts         # Date, number formatting
│   │       ├── validators.ts         # Input validation
│   │       ├── cronHelper.ts         # Cron expression parsing
│   │       ├── errorMessages.ts      # Error message templates
│   │       ├── constants.ts          # App constants
│   │       └── helpers.ts            # General utilities
│   │
│   ├── stores/
│   │   ├── authStore.ts              # Zustand auth store
│   │   ├── jobStore.ts               # Zustand jobs store
│   │   ├── uiStore.ts                # Zustand UI store
│   │   ├── executionStore.ts         # Zustand execution store
│   │   └── notificationStore.ts      # Zustand notification store
│   │
│   ├── types/
│   │   ├── api.ts                    # API response types
│   │   ├── models.ts                 # Domain models
│   │   ├── forms.ts                  # Form input types
│   │   └── index.ts                  # Type exports
│   │
│   ├── pages/
│   │   ├── LoginPage.tsx             # Login page
│   │   ├── DashboardPage.tsx         # Dashboard page
│   │   ├── JobsPage.tsx              # Jobs list page
│   │   ├── JobDetailPage.tsx         # Job detail page
│   │   ├── JobFormPage.tsx           # Create/Edit job page
│   │   ├── ExecutionsPage.tsx        # Executions history page
│   │   ├── UsersPage.tsx             # User management page (Admin)
│   │   ├── NotificationsPage.tsx     # Notifications settings
│   │   ├── SettingsPage.tsx          # User settings
│   │   ├── ProfilePage.tsx           # User profile
│   │   └── ErrorPage.tsx             # Error/404 page
│   │
│   ├── constants/
│   │   ├── api.ts                    # API endpoints
│   │   ├── roles.ts                  # Role definitions
│   │   ├── permissions.ts            # Permission matrix
│   │   ├── cronPatterns.ts           # Common cron patterns
│   │   ├── routes.ts                 # Route paths
│   │   └── messages.ts               # UI messages
│   │
│   ├── config/
│   │   ├── axios.ts                  # Axios configuration
│   │   ├── theme.ts                  # Theme configuration
│   │   ├── routes.ts                 # Route definitions
│   │   └── env.ts                    # Environment variables
│   │
│   ├── App.tsx                       # Root component
│   ├── App.css                       # App styles
│   ├── main.tsx                      # Entry point
│   └── vite-env.d.ts                 # Vite type definitions
│
├── tests/
│   ├── unit/
│   │   ├── components/
│   │   │   ├── LoginForm.test.tsx
│   │   │   ├── JobForm.test.tsx
│   │   │   └── NotificationSettings.test.tsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useAuth.test.ts
│   │   │   ├── useJobs.test.ts
│   │   │   └── usePagination.test.ts
│   │   │
│   │   ├── services/
│   │   │   ├── authService.test.ts
│   │   │   ├── jobService.test.ts
│   │   │   └── errorHandler.test.ts
│   │   │
│   │   └── utils/
│   │       ├── formatters.test.ts
│   │       ├── validators.test.ts
│   │       └── cronHelper.test.ts
│   │
│   ├── integration/
│   │   ├── auth-flow.test.tsx        # Login/logout flow
│   │   ├── job-management.test.tsx   # CRUD operations
│   │   ├── execution-tracking.test.tsx # History viewing
│   │   └── notifications.test.tsx    # Email settings
│   │
│   ├── e2e/ (Phase 9 - Optional)
│   │   ├── auth.spec.ts              # Authentication E2E
│   │   ├── jobs.spec.ts              # Job management E2E
│   │   ├── executions.spec.ts        # Execution history E2E
│   │   └── admin.spec.ts             # Admin features E2E
│   │
│   └── setup.ts                      # Test configuration
│
├── .env.example                      # Environment variables template
├── .env.development                  # Dev environment variables
├── .env.production                   # Prod environment variables
├── .eslintrc.cjs                     # ESLint configuration
├── .prettierrc.json                  # Prettier configuration
├── .gitignore                        # Git ignore rules
├── tsconfig.json                     # TypeScript configuration
├── vite.config.ts                    # Vite configuration
├── vitest.config.ts                  # Vitest configuration
├── playwright.config.ts              # Playwright config (Phase 9)
├── package.json                      # Dependencies
├── pnpm-lock.yaml                    # Dependency lock file
├── index.html                        # HTML entry point
├── README.md                         # Project README
├── ARCHITECTURE.md                   # This file
└── DEVELOPMENT.md                    # Development guidelines
```

---

## Development Phases

### Phase 1: Foundation & Setup (Week 1 - 1.5 days)
**Duration**: 1-2 days
**Goal**: Get basic project infrastructure running

#### Tasks:
1. **Project Initialization**
   - Create Vite React TypeScript project
   - Configure ESLint, Prettier, Husky
   - Set up git workflow and branch naming

2. **Environment Setup**
   - Create .env.example with all required variables
   - Configure environment-specific builds
   - Set up development server on port 5173

3. **Core Dependencies**
   - Install and configure Tailwind CSS
   - Install shadcn/ui and initialize
   - Install Zustand, Axios, React Router

4. **Configuration Files**
   - tsconfig.json with strict mode
   - vite.config.ts with plugins
   - vitest.config.ts for testing
   - axios client with interceptors

#### Deliverables:
- ✅ Project structure created
- ✅ Dev server running with HMR
- ✅ All dependencies installed
- ✅ ESLint/Prettier working
- ✅ First commit to feature branch

#### Commands:
```bash
# Create project
npm create vite@latest cron-job-frontend -- --template react-ts
cd cron-job-frontend

# Install dependencies
pnpm install

# Install additional packages
pnpm add -D @types/react @types/react-dom
pnpm add -D tailwindcss postcss autoprefixer
pnpm install -D shadcn-ui
pnpm add zustand axios zustand
pnpm add react-router-dom react-hook-form
pnpm add recharts lucide-react
pnpm add -D vitest @testing-library/react @testing-library/jest-dom @vitest/ui
pnpm add -D eslint eslint-config-airbnb-typescript prettier
pnpm add -D husky lint-staged

# Initialize git hooks
npx husky install

# Start dev server
pnpm dev

# Run tests
pnpm test
```

#### Acceptance Criteria:
- ✅ Dev server runs without errors
- ✅ TypeScript compiles with no errors
- ✅ ESLint passes without warnings
- ✅ Prettier formats code correctly
- ✅ Git hooks configured and working

---

### Phase 2: Authentication & Layout (Week 1 - 2-3 days)
**Duration**: 2-3 days
**Goal**: Implement login system and basic layout

#### Tasks:
1. **Authentication Service**
   - Create authService.ts with login/logout API calls
   - Implement JWT token storage and retrieval
   - Create request/response interceptors for token injection
   - Handle 401 errors and auto-logout

2. **Auth Store (Zustand)**
   - Create authStore with user, token, isAuthenticated state
   - Implement login, logout, setUser actions
   - Add middleware for localStorage persistence
   - Initialize auth on app load

3. **Login Page & Components**
   - Create LoginForm component with email/password
   - Add form validation with React Hook Form
   - Implement error handling and loading states
   - Add remember-me checkbox functionality
   - Style with Tailwind + shadcn/ui Button, Input

4. **Layout Components**
   - Create Layout wrapper component
   - Build Header with logo and user menu
   - Build Sidebar with navigation links
   - Create ProtectedRoute for route protection
   - Style responsive layout (desktop/mobile)

5. **Route Setup**
   - Configure React Router with protected routes
   - Create public routes (login)
   - Create private routes (dashboard, jobs, etc.)
   - Implement navigation guards

#### Deliverables:
- ✅ Login page fully functional
- ✅ JWT token stored in localStorage
- ✅ Layout components created
- ✅ Protected routes working
- ✅ 80%+ test coverage for auth components

#### Commands:
```bash
# Create auth service
touch src/services/api/authService.ts

# Create auth store
touch src/stores/authStore.ts

# Create auth components
mkdir -p src/components/auth
touch src/components/auth/LoginForm.tsx
touch src/components/auth/ProtectedRoute.tsx

# Create layout components
mkdir -p src/components/layout
touch src/components/layout/Layout.tsx
touch src/components/layout/Header.tsx
touch src/components/layout/Sidebar.tsx

# Run tests
pnpm test:phase2
```

#### Acceptance Criteria:
- ✅ Login page renders without errors
- ✅ Can submit login form
- ✅ JWT token saved to localStorage
- ✅ Protected routes redirect to login when unauthorized
- ✅ Logout clears token and redirects
- ✅ 80%+ test coverage for Phase 2

---

### Phase 3: Job Management - List & Create (Week 2 - 2-3 days)
**Duration**: 2-3 days
**Goal**: Implement job listing and creation

#### Tasks:
1. **Job Service**
   - Create jobService.ts with API calls
   - Implement getJobs(), createJob(), updateJob(), deleteJob()
   - Add query parameters for filtering/sorting/pagination
   - Handle error responses

2. **Job Store (Zustand)**
   - Create jobStore with jobs list, filters, pagination state
   - Implement load, create, update, delete actions
   - Add filter and sort actions
   - Implement pagination state

3. **Jobs List Page**
   - Create JobList component with table
   - Implement pagination controls
   - Add status filters (active, inactive, failed)
   - Add search/filter bar
   - Create JobCard component for grid view option
   - Add bulk actions (enable, disable, delete)

4. **Create/Edit Job Form**
   - Create JobForm component with form fields
   - Implement cron expression field with validation
   - Add CronExpressionHelper component for building expressions
   - Support webhook/email trigger types
   - Add retry configuration options
   - Implement form validation with React Hook Form

5. **Cron Expression Helper**
   - Create interactive cron expression builder
   - Add preset patterns (every minute, hourly, daily, weekly, etc.)
   - Show human-readable cron expression
   - Validate expression with backend

6. **UI Components**
   - Create JobFilters component
   - Create JobPagination component
   - Create status badges and indicators
   - Add loading states and skeleton loaders

#### Deliverables:
- ✅ Jobs list page displays all jobs
- ✅ Can create new job with validation
- ✅ Can edit existing job
- ✅ Can delete job with confirmation
- ✅ Pagination working correctly
- ✅ Filters functioning
- ✅ 80%+ test coverage

#### Commands:
```bash
# Create job service
touch src/services/api/jobService.ts

# Create job store
touch src/stores/jobStore.ts

# Create job components
mkdir -p src/components/jobs
touch src/components/jobs/JobList.tsx
touch src/components/jobs/JobForm.tsx
touch src/components/jobs/CronExpressionHelper.tsx
touch src/components/jobs/JobCard.tsx
touch src/components/jobs/JobFilters.tsx

# Create pages
mkdir -p src/pages
touch src/pages/JobsPage.tsx
touch src/pages/JobFormPage.tsx

# Run tests
pnpm test:phase3
```

#### Acceptance Criteria:
- ✅ Jobs list page renders with data
- ✅ Create job form submits successfully
- ✅ Validation prevents invalid cron expressions
- ✅ Pagination controls work correctly
- ✅ Filters update displayed jobs
- ✅ Delete operation with confirmation
- ✅ 80%+ test coverage for Phase 3

---

### Phase 4: Execution Tracking & History (Week 2 - 2 days)
**Duration**: 2 days
**Goal**: Display job execution history and statistics

#### Tasks:
1. **Execution Service**
   - Create executionService.ts with API calls
   - Implement getExecutions(), getExecutionDetail(), getStatistics()
   - Add filtering by job, date range, status
   - Implement pagination and sorting

2. **Execution Store (Zustand)**
   - Create executionStore with executions list, statistics
   - Implement load, filter, sort actions
   - Add pagination state
   - Cache statistics

3. **Execution List Page**
   - Create ExecutionList component with table
   - Display execution status, start/end time, duration
   - Add filters by job, date range, status
   - Implement sorting by time, duration, status
   - Add pagination
   - Link to job detail

4. **Execution Detail Page**
   - Create ExecutionDetail component
   - Display full execution information
   - Show webhook response/logs
   - Display error messages if failed
   - Show retry information if applicable

5. **Statistics Components**
   - Create ExecutionStats component
   - Show total executions, success rate, failed count
   - Display average duration, max/min duration
   - Create ExecutionCharts with Recharts
   - Show trend chart (executions per day/week)
   - Add success/failure breakdown pie chart

6. **Job Detail View**
   - Create JobDetail component
   - Display job information
   - Show recent executions
   - Display statistics summary
   - Add action buttons (edit, delete, run now)

#### Deliverables:
- ✅ Execution history page displays data
- ✅ Statistics calculated and displayed
- ✅ Charts render correctly
- ✅ Filters and sorting work
- ✅ Pagination functioning
- ✅ 80%+ test coverage

#### Commands:
```bash
# Create execution service
touch src/services/api/executionService.ts

# Create execution store
touch src/stores/executionStore.ts

# Create execution components
mkdir -p src/components/executions
touch src/components/executions/ExecutionList.tsx
touch src/components/executions/ExecutionDetail.tsx
touch src/components/executions/ExecutionStats.tsx
touch src/components/executions/ExecutionCharts.tsx

# Create pages
touch src/pages/ExecutionsPage.tsx
touch src/pages/JobDetailPage.tsx

# Run tests
pnpm test:phase4
```

#### Acceptance Criteria:
- ✅ Execution list displays with correct data
- ✅ Statistics calculated correctly
- ✅ Charts render without errors
- ✅ Filters work for all fields
- ✅ Date range filters functional
- ✅ Pagination working
- ✅ 80%+ test coverage for Phase 4

---

### Phase 5: Notifications Configuration (Week 3 - 1-2 days)
**Duration**: 1-2 days
**Goal**: Email notification settings and preview

#### Tasks:
1. **Notification Service**
   - Create notificationService.ts with API calls
   - Implement getSettings(), updateSettings(), sendTestEmail()
   - Get notification templates for preview

2. **Notification Store**
   - Create notificationStore with settings
   - Implement update and toggle actions
   - Cache settings in localStorage

3. **Notification Settings Page**
   - Create NotificationSettings component
   - Add toggle for email notifications per job
   - Implement global settings form
   - Add send test email button with feedback
   - Show notification history

4. **Email Template Preview**
   - Create NotificationPreview component
   - Display sample email templates
   - Show variables available for customization
   - Implement preview in modal

5. **Notification Preferences**
   - Create NotificationToggle component for individual jobs
   - Add dropdown for notification frequency
   - Implement webhook notification options

#### Deliverables:
- ✅ Notification settings page functional
- ✅ Can toggle email notifications
- ✅ Test email sending works
- ✅ Settings persist to backend
- ✅ Preview displays correctly
- ✅ 80%+ test coverage

#### Commands:
```bash
# Create notification service
touch src/services/api/notificationService.ts

# Create notification store
touch src/stores/notificationStore.ts

# Create notification components
mkdir -p src/components/notifications
touch src/components/notifications/NotificationSettings.tsx
touch src/components/notifications/NotificationToggle.tsx
touch src/components/notifications/NotificationPreview.tsx

# Create page
touch src/pages/NotificationsPage.tsx

# Run tests
pnpm test:phase5
```

#### Acceptance Criteria:
- ✅ Settings page loads correctly
- ✅ Can toggle notifications on/off
- ✅ Test email sends successfully
- ✅ Settings saved to backend
- ✅ Email preview displays
- ✅ 80%+ test coverage for Phase 5

---

### Phase 6: User Management (Admin Only) (Week 3 - 2-3 days)
**Duration**: 2-3 days
**Goal**: Admin user management features

#### Tasks:
1. **User Service**
   - Create userService.ts with API calls
   - Implement getUsers(), createUser(), updateUser(), deleteUser(), changePassword()
   - Add role assignment functions

2. **Users List Page**
   - Create UserList component with table
   - Display user info, role, created date, status
   - Add pagination and search
   - Add bulk actions for role change/deactivation

3. **User Create/Edit Form**
   - Create UserForm component
   - Implement email, name, role fields
   - Add password input for new users
   - Support password reset functionality
   - Role selection dropdown

4. **User Detail Page**
   - Create UserDetail component
   - Display user profile information
   - Show user statistics (jobs created, executions)
   - Show activity history
   - Add action buttons (edit, delete, reset password)

5. **Role Management**
   - Create RoleManager component
   - Display permission matrix by role
   - Allow role assignment
   - Show permission descriptions

6. **Permission Visualization**
   - Create PermissionMatrix component
   - Show role-based permissions table
   - Display what each role can do
   - Add role descriptions

#### Deliverables:
- ✅ User management page functional
- ✅ Can create new users
- ✅ Can edit user details
- ✅ Can assign roles
- ✅ Can delete users with confirmation
- ✅ Role management working
- ✅ 80%+ test coverage (Admin only)

#### Commands:
```bash
# Create user service
touch src/services/api/userService.ts

# Create user components
mkdir -p src/components/users
touch src/components/users/UserList.tsx
touch src/components/users/UserForm.tsx
touch src/components/users/UserDetail.tsx
touch src/components/users/RoleManager.tsx
touch src/components/users/PermissionMatrix.tsx

# Create page
touch src/pages/UsersPage.tsx

# Run tests (Admin only)
pnpm test:phase6
```

#### Acceptance Criteria:
- ✅ User list displays with data
- ✅ Can create user with validation
- ✅ Can edit user details
- ✅ Can assign roles correctly
- ✅ Can delete user with confirmation
- ✅ Permission matrix displays correctly
- ✅ 80%+ test coverage for Phase 6

---

### Phase 7: Dashboard & Analytics (Week 4 - 2-3 days)
**Duration**: 2-3 days
**Goal**: Main dashboard with key metrics

#### Tasks:
1. **Dashboard Page**
   - Create Dashboard component
   - Layout with grid system for widgets
   - Show key metrics and statistics
   - Responsive design for all screen sizes

2. **Statistics Cards**
   - Create StatsCard component
   - Display total jobs, successful executions, failed executions
   - Show average execution time
   - Display system health status

3. **Recent Activities**
   - Create RecentJobs component showing last 5 jobs
   - Create RecentExecutions showing last executions
   - Add links to drill down

4. **Trend Charts**
   - Create ExecutionTrend component
   - Display executions per day/week
   - Show success/failure trend
   - Implement date range picker

5. **System Health**
   - Create HealthStatus component
   - Show API health status
   - Display database status
   - Show scheduler status
   - Auto-refresh every 30 seconds

6. **User-Specific Dashboard**
   - Show only user's jobs and executions
   - Different dashboard for Admin view
   - Quick action buttons
   - Job creation shortcut

#### Deliverables:
- ✅ Dashboard page renders correctly
- ✅ All widgets display data
- ✅ Charts render without errors
- ✅ Auto-refresh functionality working
- ✅ Responsive on all screen sizes
- ✅ 80%+ test coverage

#### Commands:
```bash
# Create dashboard components
mkdir -p src/components/dashboard
touch src/components/dashboard/Dashboard.tsx
touch src/components/dashboard/StatsCard.tsx
touch src/components/dashboard/RecentJobs.tsx
touch src/components/dashboard/ExecutionTrend.tsx
touch src/components/dashboard/HealthStatus.tsx

# Create page
touch src/pages/DashboardPage.tsx

# Run tests
pnpm test:phase7
```

#### Acceptance Criteria:
- ✅ Dashboard loads without errors
- ✅ All widgets display correct data
- ✅ Charts render properly
- ✅ Statistics calculated correctly
- ✅ Auto-refresh working
- ✅ Responsive design functioning
- ✅ 80%+ test coverage for Phase 7

---

### Phase 8: Polish & Performance (Week 4 - 2-3 days)
**Duration**: 2-3 days
**Goal**: Optimize, test, and prepare for production

#### Tasks:
1. **Performance Optimization**
   - Implement code splitting with React.lazy and Suspense
   - Optimize bundle size (check with Vite analyzer)
   - Implement image optimization
   - Add service worker for offline support
   - Lazy load charts and heavy components

2. **Error Handling & Validation**
   - Implement global error boundary
   - Add comprehensive error messages
   - Implement form validation for all inputs
   - Add field-level validation feedback
   - Create error page with helpful information

3. **Accessibility**
   - Add ARIA labels to all interactive elements
   - Ensure keyboard navigation works
   - Test with screen readers
   - Add focus management
   - Ensure color contrast compliance

4. **Responsive Design**
   - Test on mobile, tablet, desktop
   - Implement mobile-first approach
   - Add touch-friendly interactions
   - Implement responsive tables
   - Test landscape/portrait modes

5. **Dark Mode Support**
   - Implement theme toggle in settings
   - Use Tailwind dark: prefix
   - Save preference to localStorage
   - Apply to all components

6. **Loading States & Skeletons**
   - Add skeleton loaders for all data tables
   - Implement loading spinners for async operations
   - Add progress indicators
   - Implement optimistic updates

7. **Internationalization (i18n) - Optional**
   - Extract all strings to translation keys
   - Set up i18n library (react-i18next)
   - Create English translations
   - Support for multiple languages structure

8. **End-to-End Testing**
   - Write E2E tests for critical flows
   - Test authentication flow
   - Test job creation flow
   - Test execution tracking flow
   - Test admin user management

#### Deliverables:
- ✅ Bundle size optimized
- ✅ All pages perform well (LCP < 2.5s)
- ✅ Accessibility compliance checked
- ✅ Responsive design tested
- ✅ Dark mode working
- ✅ Error boundaries active
- ✅ E2E tests passing
- ✅ 85%+ overall test coverage

#### Commands:
```bash
# Analyze bundle size
pnpm run build
npm run analyze

# Run all tests
pnpm test

# Build production
pnpm build

# Preview production build
pnpm preview

# Run E2E tests
pnpm e2e

# Check accessibility
pnpm audit-a11y
```

#### Acceptance Criteria:
- ✅ Bundle size < 250KB gzipped
- ✅ All lighthouse scores > 80
- ✅ No console errors or warnings
- ✅ Mobile responsive (tested on 375px+)
- ✅ Dark mode working properly
- ✅ All links have ARIA labels
- ✅ Keyboard navigation functional
- ✅ 85%+ test coverage overall
- ✅ E2E critical flows passing

---

### Phase 9: Advanced Features (Optional - Week 5)
**Duration**: 1-2 weeks (Optional)
**Goal**: Additional features for enhanced functionality

#### Tasks:
1. **Real-Time Updates**
   - Implement WebSocket connection for live job updates
   - Push notifications for job completions
   - Live status updates without refresh
   - Subscribe to job execution events

2. **Job Scheduling Wizard**
   - Create multi-step wizard for job creation
   - Visual cron builder with calendar
   - Template selection (database backup, API call, etc.)
   - Parameter builder for dynamic values

3. **Audit Logging**
   - Display audit log of all user actions
   - Filter by user, action, date
   - Export audit logs
   - Show who did what and when

4. **Job Templates**
   - Create reusable job templates
   - Template marketplace/gallery
   - Clone job from template
   - Save current job as template

5. **Advanced Reporting**
   - Generate PDF reports
   - Schedule report delivery via email
   - Chart export functionality
   - Custom report builder

6. **Webhook Management**
   - Display webhook details
   - Test webhook functionality
   - Retry failed webhooks
   - View webhook payloads

7. **Multi-Tenancy (If Backend Supports)**
   - Organization/workspace switching
   - Shared jobs within organization
   - Organization-level settings
   - Billing dashboard

8. **API Integration Examples**
   - Show integration examples
   - API documentation viewer
   - Code snippets for different languages
   - Postman collection generation

#### Deliverables:
- ✅ Real-time updates working
- ✅ Scheduling wizard fully functional
- ✅ Audit logs displaying correctly
- ✅ Templates working as expected
- ✅ Reports generating successfully
- ✅ 80%+ test coverage for Phase 9

#### Commands:
```bash
# Start WebSocket server (if implemented)
# Run advanced feature tests
pnpm test:phase9

# Generate reports
pnpm run reports

# Build advanced features
pnpm build
```

#### Acceptance Criteria:
- ✅ WebSocket connection stable
- ✅ Real-time updates working
- ✅ Wizard captures all inputs
- ✅ Audit logs complete
- ✅ Templates function correctly
- ✅ Reports generate without errors
- ✅ 80%+ test coverage for Phase 9

---

## Implementation Details

### Authentication Flow

```
Login Form
    ↓
Submit Credentials
    ↓
authService.login() → POST /api/auth/login
    ↓
Backend validates → Returns JWT + user info
    ↓
authStore.setAuth() → Store token + user
    ↓
tokenStorage.save() → Save to localStorage
    ↓
Navigate to Dashboard
    ↓
Request Interceptor adds token to headers
    ↓
API calls include Authorization: Bearer <token>
    ↓
Response Interceptor checks status
    ↓
If 401 → Clear auth + redirect to login
```

### API Integration Pattern

```typescript
// services/api/jobService.ts
import { client } from './client';
import { Job, CreateJobRequest, UpdateJobRequest } from '@/types';

export const jobService = {
  async getJobs(params?: QueryParams): Promise<Job[]> {
    const { data } = await client.get('/api/jobs', { params });
    return data;
  },

  async createJob(data: CreateJobRequest): Promise<Job> {
    const response = await client.post('/api/jobs', data);
    return response.data;
  },

  async updateJob(id: string, data: UpdateJobRequest): Promise<Job> {
    const response = await client.put(`/api/jobs/${id}`, data);
    return response.data;
  },

  async deleteJob(id: string): Promise<void> {
    await client.delete(`/api/jobs/${id}`);
  },
};
```

### State Management Pattern (Zustand)

```typescript
// stores/jobStore.ts
import { create } from 'zustand';

interface JobStore {
  jobs: Job[];
  isLoading: boolean;
  error: string | null;
  
  // Actions
  loadJobs: () => Promise<void>;
  addJob: (job: Job) => void;
  updateJob: (id: string, job: Partial<Job>) => void;
  deleteJob: (id: string) => void;
  setError: (error: string | null) => void;
}

export const useJobStore = create<JobStore>((set) => ({
  jobs: [],
  isLoading: false,
  error: null,

  loadJobs: async () => {
    set({ isLoading: true });
    try {
      const jobs = await jobService.getJobs();
      set({ jobs, error: null });
    } catch (error) {
      set({ error: error.message });
    } finally {
      set({ isLoading: false });
    }
  },

  addJob: (job) => set((state) => ({ jobs: [...state.jobs, job] })),
  
  updateJob: (id, updatedJob) =>
    set((state) => ({
      jobs: state.jobs.map((job) =>
        job.id === id ? { ...job, ...updatedJob } : job
      ),
    })),

  deleteJob: (id) =>
    set((state) => ({
      jobs: state.jobs.filter((job) => job.id !== id),
    })),

  setError: (error) => set({ error }),
}));
```

### Custom Hook Pattern

```typescript
// hooks/useJobs.ts
import { useCallback, useEffect } from 'react';
import { useJobStore } from '@/stores/jobStore';

export const useJobs = () => {
  const { jobs, isLoading, error, loadJobs } = useJobStore();

  useEffect(() => {
    loadJobs();
  }, []);

  const refreshJobs = useCallback(() => {
    loadJobs();
  }, [loadJobs]);

  return { jobs, isLoading, error, refreshJobs };
};
```

### Form Component Pattern

```typescript
// components/jobs/JobForm.tsx
import { useForm, Controller } from 'react-hook-form';
import { Button, Input, Select } from '@/components/ui';

interface JobFormProps {
  initialData?: Job;
  onSubmit: (data: CreateJobRequest) => Promise<void>;
}

export const JobForm: React.FC<JobFormProps> = ({ initialData, onSubmit }) => {
  const { control, handleSubmit, formState: { errors, isSubmitting } } = useForm({
    defaultValues: initialData,
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <Controller
        control={control}
        name="name"
        rules={{ required: 'Job name is required' }}
        render={({ field }) => (
          <Input
            {...field}
            placeholder="Job name"
            error={errors.name?.message}
          />
        )}
      />
      
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Saving...' : 'Save Job'}
      </Button>
    </form>
  );
};
```

---

## Integration Points

### Backend API Base
```
Base URL: http://localhost:5001/api
Environment: Configured in .env.development
```

### Key API Endpoints

#### Authentication
```
POST   /auth/login
POST   /auth/logout
POST   /auth/refresh
GET    /auth/me
```

#### Jobs
```
GET    /jobs                    # List all jobs
POST   /jobs                    # Create job
GET    /jobs/{id}               # Get job details
PUT    /jobs/{id}               # Update job
DELETE /jobs/{id}               # Delete job
POST   /jobs/{id}/run           # Run job immediately
GET    /jobs/{id}/executions    # Get job executions
```

#### Executions
```
GET    /executions              # List executions
GET    /executions/{id}         # Get execution details
GET    /executions/{id}/logs    # Get execution logs
GET    /statistics              # Get statistics
```

#### Users (Admin Only)
```
GET    /users                   # List users
POST   /users                   # Create user
GET    /users/{id}              # Get user details
PUT    /users/{id}              # Update user
DELETE /users/{id}              # Delete user
POST   /users/{id}/reset-password # Reset password
```

#### Notifications
```
GET    /notifications/settings  # Get settings
PUT    /notifications/settings  # Update settings
POST   /notifications/test      # Send test email
```

#### Health
```
GET    /health                  # System health
```

---

## Testing Strategy

### Unit Testing
- Test individual components in isolation
- Mock API calls using vi.mock()
- Test hooks with @testing-library/react hooks
- Test utility functions with Vitest
- Target: 80%+ coverage per component

### Integration Testing
- Test component interactions
- Test form submission flows
- Test API integration with mocked responses
- Test store interactions
- Target: 80%+ coverage per integration

### E2E Testing (Phase 9)
- Test complete user workflows
- Test authentication flow end-to-end
- Test job creation to execution
- Test user management flows
- Target: All critical paths covered

### Test Naming Convention
```
describe('[Component/Function Name]', () => {
  describe('[Behavior]', () => {
    it('should [expected outcome] when [condition]', () => {
      // Arrange
      // Act
      // Assert
    });
  });
});
```

### Running Tests
```bash
# Run all tests
pnpm test

# Run tests in watch mode
pnpm test:watch

# Run tests with coverage
pnpm test:coverage

# Run tests by phase
pnpm test:phase1
pnpm test:phase2
# ... etc

# Run E2E tests
pnpm e2e

# Run specific file
pnpm test -- JobForm.test.tsx
```

---

## Deployment

### Development
```bash
# Install dependencies
pnpm install

# Start dev server (http://localhost:5173)
pnpm dev

# Run tests
pnpm test

# Build for testing
pnpm build
pnpm preview
```

### Staging
```bash
# Build
VITE_API_URL=https://staging-api.example.com pnpm build

# Deploy to staging
# Use Netlify/Vercel CI/CD or manual deployment
```

### Production

#### Option 1: Vercel
```bash
# Connect repository to Vercel
# Set environment variables in Vercel dashboard
# Auto-deploys on push to main branch

# Manual deployment
pnpm build
vercel --prod
```

#### Option 2: Netlify
```bash
# Connect repository to Netlify
# Set build command: pnpm build
# Set publish directory: dist
# Set environment variables in Netlify dashboard
# Auto-deploys on push to main branch
```

#### Option 3: Docker
```dockerfile
# Dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install
COPY . .
RUN pnpm build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

#### Option 4: AWS S3 + CloudFront
```bash
# Build
pnpm build

# Deploy to S3
aws s3 sync dist/ s3://bucket-name

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"
```

### Environment Variables
```
# .env.development
VITE_API_URL=http://localhost:5001/api
VITE_APP_NAME=Cron Job Manager
VITE_APP_VERSION=1.0.0

# .env.production
VITE_API_URL=https://api.example.com/api
VITE_APP_NAME=Cron Job Manager
VITE_APP_VERSION=1.0.0
VITE_ANALYTICS_ID=your-analytics-id
```

---

## Git Workflow

### Branch Naming
```
feature/phase-1-auth          # Feature for specific phase
fix/login-button-styling      # Bug fix
docs/update-readme            # Documentation
chore/upgrade-dependencies    # Maintenance
```

### Commit Conventions
```
feat: Add login component for Phase 1
fix: Resolve token expiration handling
docs: Update API integration guide
style: Format JobList component
refactor: Extract API client logic
test: Add tests for AuthStore
chore: Upgrade React to 18.3
```

### Pull Request Template
```markdown
## Description
Brief description of changes

## Phase
Phase 2: Authentication & Layout

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] 80%+ coverage maintained
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style
- [ ] ESLint passes
- [ ] Tests pass
- [ ] Documentation updated
- [ ] No console warnings
```

---

## Development Checklist

### Before Starting Phase
- [ ] Read phase description thoroughly
- [ ] Check backend API endpoints for required fields
- [ ] Review acceptance criteria
- [ ] Create feature branch: `git checkout -b feature/phase-X`

### During Phase Development
- [ ] Create component structure
- [ ] Implement API service functions
- [ ] Create Zustand store if needed
- [ ] Build components with TypeScript types
- [ ] Add form validation
- [ ] Implement error handling
- [ ] Add loading states
- [ ] Style with Tailwind CSS
- [ ] Write unit tests (80%+ coverage target)
- [ ] Test in browser
- [ ] Test responsive design

### After Phase Development
- [ ] Verify ESLint passes: `pnpm lint`
- [ ] Verify Prettier formatting: `pnpm format`
- [ ] Run all tests: `pnpm test:phaseX`
- [ ] Check test coverage: `pnpm test:coverage`
- [ ] Build production: `pnpm build`
- [ ] Preview build: `pnpm preview`
- [ ] Create pull request
- [ ] Request code review
- [ ] Merge to main after approval
- [ ] Deploy to staging

### Phase Gate Requirements
Each phase must meet these criteria before proceeding:
- ✅ All acceptance criteria met
- ✅ 80%+ test coverage for phase components
- ✅ No TypeScript errors
- ✅ ESLint passes without warnings
- ✅ Code reviewed and approved
- ✅ Manual testing completed
- ✅ Responsive design verified
- ✅ No console errors/warnings

---

## Development Tips

### Component Structure
```typescript
// Use named exports for easier testing
export interface Props {
  // ... props
}

export const MyComponent: React.FC<Props> = ({ ... }) => {
  // component logic
};
```

### API Error Handling
```typescript
try {
  const data = await jobService.getJobs();
  // handle success
} catch (error) {
  if (error.response?.status === 401) {
    // Handle unauthorized
  } else if (error.response?.status === 404) {
    // Handle not found
  } else {
    // Handle other errors
  }
}
```

### Type Safety
```typescript
// Always define types for API responses
interface Job {
  id: string;
  name: string;
  cron_expression: string;
  // ... other fields
}

// Use types in API calls
const job: Job = await jobService.getJob(id);
```

### Testing Best Practices
```typescript
// Use descriptive test names
// Use userEvent instead of fireEvent
// Query by accessible role when possible
// Avoid testing implementation details

test('should display error message when login fails', async () => {
  // Arrange
  const user = userEvent.setup();
  render(<LoginForm />);
  
  // Act
  await user.type(screen.getByLabelText(/email/i), 'test@example.com');
  await user.click(screen.getByRole('button', { name: /login/i }));
  
  // Assert
  expect(screen.getByText(/login failed/i)).toBeInTheDocument();
});
```

### Performance Optimization
```typescript
// Lazy load routes
const Dashboard = lazy(() => import('@/pages/DashboardPage'));

// Memoize components
export const JobCard = memo(({ job }: Props) => {
  // component
});

// Use useCallback for event handlers
const handleDelete = useCallback(() => {
  deleteJob(id);
}, [id]);
```

---

## Troubleshooting

### Common Issues

**Dev Server Won't Start**
```bash
# Clear node_modules and reinstall
rm -rf node_modules pnpm-lock.yaml
pnpm install

# Clear Vite cache
rm -rf .vite

# Try again
pnpm dev
```

**TypeScript Errors**
```bash
# Check tsconfig
pnpm tsc --noEmit

# Fix issues
pnpm format

# Rebuild
pnpm dev
```

**Tests Failing**
```bash
# Run single test file
pnpm test JobForm.test.tsx

# Run with debug
pnpm test -- --inspect-brk

# Clear cache
pnpm test -- --clearCache
```

**Build Errors**
```bash
# Check build output
pnpm build

# Analyze bundle
pnpm run analyze

# Fix large imports
# Use dynamic imports for heavy libraries
```

**API Connection Issues**
```bash
# Verify backend is running
curl http://localhost:5001/api/health

# Check API URL in .env
cat .env.development | grep VITE_API_URL

# Check browser console for CORS errors
```

---

## Resources

### Documentation
- [React 18 Documentation](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs)
- [Vite Guide](https://vitejs.dev/guide)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [shadcn/ui](https://ui.shadcn.com)
- [Zustand](https://github.com/pmndrs/zustand)
- [Axios](https://axios-http.com)
- [React Router](https://reactrouter.com)
- [React Hook Form](https://react-hook-form.com)
- [Recharts](https://recharts.org)
- [Vitest](https://vitest.dev)
- [React Testing Library](https://testing-library.com/react)

### Communities
- [React Discord](https://discord.gg/react)
- [Stack Overflow React Tag](https://stackoverflow.com/questions/tagged/reactjs)
- [GitHub Discussions](https://github.com/facebook/react/discussions)

### Tools
- [VS Code Extensions](https://marketplace.visualstudio.com) - ES7+ React/Redux, Prettier, ESLint
- [React DevTools](https://react-devtools-tutorial.vercel.app)
- [Redux DevTools](https://github.com/reduxjs/redux-devtools)

---

## Summary

This architecture provides a structured, phase-by-phase approach to building the frontend for the Cron Job Management System. Each phase builds upon the previous one, ensuring incremental progress and testability.

**Key Principles:**
1. Progressive development with clear phases
2. TypeScript for type safety
3. 80%+ test coverage requirement per phase
4. Responsive design for all screen sizes
5. Accessible components following WCAG guidelines
6. Clean code with ESLint and Prettier
7. Comprehensive error handling
8. Performance optimization throughout

**Expected Timeline:**
- Phase 1-2: Week 1 (Foundation + Auth)
- Phase 3-4: Week 2 (Job Management + Execution)
- Phase 5-6: Week 3 (Notifications + Users)
- Phase 7-8: Week 4 (Dashboard + Polish)
- Phase 9: Week 5+ (Optional Advanced Features)

Start with Phase 1 and progress through each phase, ensuring all acceptance criteria are met before moving forward.
