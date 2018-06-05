%{?!dnf_lowest_compatible: %global dnf_lowest_compatible 2.7.0}
%{?!dnf_not_compatible: %global dnf_not_compatible 3.0}
%global hawkey_version 0.7.0

%if 0%{?rhel} && 0%{?rhel} <= 7
%bcond_with python3
%else
%bcond_without python3
%endif

Name:           dnf-plugin-offline-upgrade
Version:        0.1.0
Release:        1%{?dist}
Summary:        Offline Upgrade Plugin for DNF
License:        GPLv2+
URL:            https://github.com/leapp-to/dnf-plugin-offline-upgrade
Source0:        %{url}/archive/%{name}-%{version}/%{name}-%{version}.tar.gz
BuildArch:      noarch
BuildRequires:  cmake
%if %{with python3}
Requires:       python3-%{name} = %{version}-%{release}
%else
Requires:       python2-%{name} = %{version}-%{release}
%endif
Provides:       dnf-command(offline-upgrade)
Provides:       dnf-plugin-offline-upgrade = %{version}-%{release}

%description
Offline Upgrade Plugin for DNF

%package -n python2-%{name}
Summary:        Offline Upgrade Plugin for DNF
%{?python_provide:%python_provide python2-%{name}}
BuildRequires:  python2-dnf >= %{dnf_lowest_compatible}
BuildRequires:  python2-dnf < %{dnf_not_compatible}
BuildRequires:  python2-devel
Requires:       python2-dnf >= %{dnf_lowest_compatible}
Requires:       python2-dnf < %{dnf_not_compatible}
Requires:       python2-hawkey >= %{hawkey_version}
Provides:       python2-%{name} = %{version}-%{release}
Conflicts:      python3-%{name} < %{version}-%{release}
Conflicts:      python-%{name} < %{version}-%{release}

%description -n python2-%{name}
Offline Upgrade Plugin for DNF

%if %{with python3}
%package -n python3-%{name}
Summary:    Offline Upgrade Plugin for DNF
%{?python_provide:%python_provide python3-%{name}}
BuildRequires:  python3-devel
BuildRequires:  python3-dnf >= %{dnf_lowest_compatible}
BuildRequires:  python3-dnf < %{dnf_not_compatible}
Requires:       python3-dnf >= %{dnf_lowest_compatible}
Requires:       python3-dnf < %{dnf_not_compatible}
Requires:       python3-hawkey >= %{hawkey_version}
Provides:       python3-%{name} = %{version}-%{release}
Conflicts:      python2-%{name} < %{version}-%{release}
Conflicts:      python-%{name} < %{version}-%{release}

%description -n python3-%{name}
Offline Upgrade Plugin for DNF
%endif

%prep
%autosetup
mkdir build-py2
%if %{with python3}
mkdir build-py3
%endif

%build
pushd build-py2
  %cmake ../
  %make_build
popd
%if %{with python3}
pushd build-py3
  %cmake ../ -DPYTHON_DESIRED:str=3
  %make_build
popd
%endif

%install
pushd build-py2
  %make_install
popd
%if %{with python3}
pushd build-py3
  %make_install
popd
%endif

%files -n python2-%{name}
%doc README.rst
%{python2_sitelib}/dnf-plugins/offline_upgrade.*

%if %{with python3}
%files -n python3-%{name}
%doc README.rst
%{python3_sitelib}/dnf-plugins/offline_upgrade.py
%{python3_sitelib}/dnf-plugins/__pycache__/offline_upgrade.*
%endif

%changelog
* Tue Jun 05 2018 Arthur Mello <amello@redhat.com> - 0.1.0-1
- Initial build
