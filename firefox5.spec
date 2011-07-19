%define fedora 12

# Separated plugins are supported on x86(64) only
%ifarch %{ix86} x86_64
%define separated_plugins 1
%else
%define separated_plugins 0
%endif

%define homepage http://start.fedoraproject.org/
%define default_bookmarks_file %{_datadir}/bookmarks/default-bookmarks.html
%define firefox_app_id \{ec8030f7-c20a-464f-9b0e-13a3a9e97384\}

%global shortname       firefox
#global mycomment       RC Build 1 candidate
%global firefox_dir_ver 5
%global gecko_version   5.0
%global alpha_version   0
%global beta_version    0
%global rc_version      0
%global datelang        20110624

%global mozappdir     %{_libdir}/%{shortname}-%{firefox_dir_ver}
%global langpackdir   %{mozappdir}/langpacks
%global tarballdir    mozilla-release

%define official_branding       1
%define build_langpacks         1
%define include_debuginfo       0

%if %{alpha_version} > 0
%global pre_version a%{alpha_version}
%global pre_name    alpha%{alpha_version}
%endif
%if %{beta_version} > 0
%global pre_version b%{beta_version}
%global pre_name    beta%{beta_version}
%endif
%if %{rc_version} > 0
%global pre_version rc%{rc_version}
%global pre_name    rc%{rc_version}
%endif
%if %{defined pre_version}
%global gecko_verrel %{gecko_version}-%{pre_name}
%global pre_tag .%{pre_version}
%else
%global gecko_verrel %{gecko_version}-1
%endif

Summary:        Mozilla Firefox Web browser
Name:           %{shortname}
Version:        5.0
Release:        1%{?pre_tag}.el6.R
URL:            http://www.mozilla.org/projects/firefox/
License:        MPLv1.1 or GPLv2+ or LGPLv2+
Group:          Applications/Internet
Source0:        ftp://ftp.mozilla.org/pub/firefox/releases/5.0/source/firefox-%{version}.source.tar.bz2
%if %{build_langpacks}
Source1:        firefox-langpacks-%{version}%{?pre_version}-%{datelang}.tar.bz2
%endif
Source10:       firefox-mozconfig
Source11:       firefox-mozconfig-branded
Source12:       firefox-redhat-default-prefs.js
Source13:       firefox-mozconfig-debuginfo
Source20:       firefox.desktop
Source21:       firefox.sh.in
Source23:       firefox.1

#Build patches
Patch0:         firefox-version.patch
Patch1:         firefox-5.0-cache-build.patch

# Fedora patches
Patch12:        firefox-stub.patch
Patch13:        firefox-5.0-xulstub.patch

# Upstream patches
Patch30:        firefox-4.0-moz-app-launcher.patch
Patch31:        firefox-4.0-gnome3.patch

%if %{official_branding}
# Required by Mozilla Corporation


%else
# Not yet approved by Mozillla Corporation


%endif

# ---------------------------------------------------

BuildRequires:  desktop-file-utils
BuildRequires:  system-bookmarks
BuildRequires:  gecko-devel = %{gecko_verrel}
%if %{fedora} >= 16
%global xulbin xulrunner
#%global grecnf gre
%else
%global xulbin xulrunner5
#%global grecnf gre5
%endif
# For WebM support
BuildRequires:	yasm

Requires:       gecko-libs%{?_isa} = %{gecko_verrel}
Requires:       system-bookmarks
Obsoletes:      mozilla <= 37:1.7.13
Provides:       webclient
%if %{name} == %{shortname}
Obsoletes:      firefox5
Provides:       firefox5 = %{version}-%{release}
%endif


%description
Mozilla Firefox is an open-source web browser, designed for standards
compliance, performance and portability.

#---------------------------------------------------------------------

%prep
echo TARGET = %{name}-%{version}-%{release}%{?dist}
[ -f %{SOURCE1} ] || exit 1
%setup -q -c
cd %{tarballdir}

sed -e 's/__RPM_VERSION_INTERNAL__/%{firefox_dir_ver}/' %{P:%%PATCH0} \
    > version.patch
%{__patch} -p1 -b --suffix .version --fuzz=0 < version.patch
    

# Build patches
%patch1 -p2 -b .cache

# For branding specific patches.

# Fedora patches
%patch12 -p2 -b .stub
%patch13 -p1 -R -b .xulstub

# Upstream patches
%patch30 -p1 -b .moz-app-launcher
%patch31 -p1 -b .gnome3

%if %{official_branding}
# Required by Mozilla Corporation

%else
# Not yet approved by Mozilla Corporation
%endif


%{__rm} -f .mozconfig
%{__cat} %{SOURCE10} \
%if %{fedora} < 15
  | grep -v enable-system-sqlite   \
%endif
%if %{fedora} < 13
  | grep -v with-system-nspr       \
  | grep -v with-system-nss        \
%endif
%if %{fedora} < 11
  | grep -v enable-system-hunspell \
%endif
%if %{fedora} < 15
  | grep -v enable-system-cairo    \
%endif
%ifarch %{ix86} x86_64
  | grep -v disable-necko-wifi     \
%endif
  | tee .mozconfig

%if %{official_branding}
%{__cat} %{SOURCE11} >> .mozconfig
%endif
%if %{include_debuginfo}
%{__cat} %{SOURCE13} >> .mozconfig
%endif

echo "ac_add_options --enable-system-lcms" >> .mozconfig

# Set up SDK path
echo "ac_add_options --with-libxul-sdk=\
`pkg-config --variable=sdkdir libxul`" >> .mozconfig

%if !%{?separated_plugins}
echo "ac_add_options --disable-ipc" >> .mozconfig
%endif

%if %{fedora} < 14
echo "ac_add_options --disable-libjpeg-turbo" >> .mozconfig
%endif

# Temporary hack
sed -i -e 's/@PRE_RELEASE_SUFFIX@//' browser/base/content/browser.xul

#---------------------------------------------------------------------

%build
cd %{tarballdir}

# Mozilla builds with -Wall with exception of a few warnings which show up
# everywhere in the code; so, don't override that.
#
# Disable C++ exceptions since Mozilla code is not exception-safe
#
MOZ_OPT_FLAGS=$(echo $RPM_OPT_FLAGS -fPIC | \
                     %{__sed} -e 's/-Wall//' -e 's/-fexceptions/-fno-exceptions/g')
export CFLAGS=$MOZ_OPT_FLAGS
export CXXFLAGS=$MOZ_OPT_FLAGS

export PREFIX='%{_prefix}'
export LIBDIR='%{_libdir}'

MOZ_SMP_FLAGS=-j1
# On x86 architectures, Mozilla can build up to 4 jobs at once in parallel,
# however builds tend to fail on other arches when building in parallel.
%ifarch %{ix86} x86_64
[ -z "$RPM_BUILD_NCPUS" ] && \
     RPM_BUILD_NCPUS="`/usr/bin/getconf _NPROCESSORS_ONLN`"
[ "$RPM_BUILD_NCPUS" -ge 2 ] && MOZ_SMP_FLAGS=-j2
[ "$RPM_BUILD_NCPUS" -ge 4 ] && MOZ_SMP_FLAGS=-j4
%endif

export LDFLAGS="-Wl,-rpath,%{mozappdir}"
make -f client.mk build STRIP="/bin/true" MOZ_MAKE_FLAGS="$MOZ_SMP_FLAGS"

# create debuginfo for crash-stats.mozilla.com
%if %{include_debuginfo}
#cd %{moz_objdir}
make buildsymbols
%endif

#---------------------------------------------------------------------

%install
cd %{tarballdir}

# SPOT: We need to make these symlinks, because it is easier to do that than to hack up 
# the install scripts.
ln -s %{xulrunner_libdir}/xpcshell dist/bin/xpcshell

# set up our prefs and add it to the package manifest file, so it gets pulled in
# to omni.jar which gets created during make install
%{__cp} %{SOURCE12} dist/bin/defaults/preferences/all-redhat.js
# This sed call "replaces" firefox.js with all-redhat.js, newline, and itself (&)
# having the net effect of prepending all-redhat.js above firefox.js
%{__sed} -i -e\
    's|@BINPATH@/@PREF_DIR@/firefox.js|@BINPATH@/@PREF_DIR@/all-redhat.js\n&|' \
    browser/installer/package-manifest.in

# set up our default bookmarks
%{__cp} -p %{default_bookmarks_file} dist/bin/defaults/profile/bookmarks.html

# Make sure locale works for langpacks
%{__cat} > dist/bin/defaults/preferences/firefox-l10n.js << EOF
pref("general.useragent.locale", "chrome://global/locale/intl.properties");
EOF

# resolves bug #461880
%{__cat} > dist/bin/chrome/en-US/locale/branding/browserconfig.properties << EOF
browser.startup.homepage=%{homepage}
EOF

DESTDIR=$RPM_BUILD_ROOT make install

%{__mkdir_p} $RPM_BUILD_ROOT{%{_libdir},%{_bindir},%{_datadir}/applications}

sed -e 's/^Name=.*/Name=Firefox %{version} %{?mycomment}/' \
    -e "s/firefox/%{name}/" \
    %{SOURCE20} | tee %{name}.desktop

desktop-file-install --vendor mozilla \
  --dir $RPM_BUILD_ROOT%{_datadir}/applications \
  --delete-original %{name}.desktop 

# set up the firefox start script
%{__rm} -rf $RPM_BUILD_ROOT%{_bindir}/%{shortname}
XULRUNNER_DIR=`pkg-config --variable=libdir libxul | %{__sed} -e "s,%{_libdir},,g"`
%{__cat} %{SOURCE21} | %{__sed} -e 's,FIREFOX_VERSION,%{firefox_dir_ver},g' \
		     | %{__sed} -e "s,XULRUNNER_DIRECTORY,$XULRUNNER_DIR,g"  \
		     | %{__sed} -e "s,XULRUNNER_BIN,%{xulbin},g"  \
		     | %{__sed} -e "s,FIREFOX_BIN,%{name},g" \
  > $RPM_BUILD_ROOT%{_bindir}/%{name}
%{__chmod} 755 $RPM_BUILD_ROOT%{_bindir}/%{name}

# Remove binary stub from xulrunner
%{__rm} -rf $RPM_BUILD_ROOT/%{mozappdir}/%{shortname}


%{__install} -p -D -m 644 %{SOURCE23} $RPM_BUILD_ROOT%{_mandir}/man1/%{name}.1

%{__rm} -f $RPM_BUILD_ROOT/%{mozappdir}/firefox-config

for s in 16 22 24 32 48 256; do
    %{__mkdir_p} $RPM_BUILD_ROOT%{_datadir}/icons/hicolor/${s}x${s}/apps
    %{__cp} -p other-licenses/branding/%{shortname}/default${s}.png \
               $RPM_BUILD_ROOT%{_datadir}/icons/hicolor/${s}x${s}/apps/%{name}.png
done

echo > ../%{name}.lang
%if %{build_langpacks}
# Extract langpacks, make any mods needed, repack the langpack, and install it.
%{__mkdir_p} $RPM_BUILD_ROOT%{langpackdir}
%{__tar} xf %{SOURCE1}
for langpack in `ls firefox-langpacks/*.xpi`; do
  language=`basename $langpack .xpi`
  extensionID=langpack-$language@firefox.mozilla.org
  %{__mkdir_p} $extensionID
  unzip -q $langpack -d $extensionID
  find $extensionID -type f | xargs chmod 644

  sed -i -e "s|browser.startup.homepage.*$|browser.startup.homepage=%{homepage}|g;" \
     $extensionID/chrome/$language/locale/branding/browserconfig.properties

  cd $extensionID
  zip -qr9mX ../${extensionID}.xpi *
  cd -

  %{__install} -m 644 ${extensionID}.xpi $RPM_BUILD_ROOT%{langpackdir}
  language=`echo $language | sed -e 's/-/_/g'`
  echo "%%lang($language) %{langpackdir}/${extensionID}.xpi" >> ../%{name}.lang
done
%{__rm} -rf firefox-langpacks
%endif # build_langpacks

# System extensions
%{__mkdir_p} $RPM_BUILD_ROOT%{_datadir}/mozilla/extensions/%{firefox_app_id}
%{__mkdir_p} $RPM_BUILD_ROOT%{_libdir}/mozilla/extensions/%{firefox_app_id}

# Copy over the LICENSE
%{__install} -p -c -m 644 LICENSE $RPM_BUILD_ROOT/%{mozappdir}

# Enable crash reporter for Firefox application
%if %{include_debuginfo}
sed -i -e "s/\[Crash Reporter\]/[Crash Reporter]\nEnabled=1/" $RPM_BUILD_ROOT/%{mozappdir}/application.ini
%endif

# Install our xulrunner stub
%{__rm} -f $RPM_BUILD_ROOT/%{mozappdir}/firefox
%{__cp} xulrunner/stub/xulrunner-stub $RPM_BUILD_ROOT/%{mozappdir}/firefox

#---------------------------------------------------------------------

%pre
echo -e "\nWARNING : This %{name} %{version} %{?mycomment} RPM is not an official"
echo -e "Fedora build and it overrides the official one. Don't file bugs on Fedora Project.\n"
echo -e "Use dedicated forums http://forums.famillecollet.com/\n"

%if %{?fedora}%{!?fedora:99} <= 13
echo -e "WARNING : Fedora %{fedora} is now EOL :"
echo -e "You should consider upgrading to a supported release.\n"
%endif

%if %{name} == %{shortname}
%preun
# is it a final removal?
if [ $1 -eq 0 ]; then
  %{__rm} -rf %{mozappdir}/components
  %{__rm} -rf %{mozappdir}/extensions
  %{__rm} -rf %{mozappdir}/plugins
  %{__rm} -rf %{langpackdir}
fi
%endif

%post
update-desktop-database &> /dev/null || :
touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :
gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :

%postun
update-desktop-database &> /dev/null || :
if [ $1 -eq 0 ] ; then
    touch --no-create %{_datadir}/icons/hicolor &>/dev/null
    gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :
fi


%files -f %{name}.lang
%defattr(-,root,root,-)
%{_bindir}/%{name}
%{mozappdir}/firefox
%doc %{_mandir}/man1/*
%dir %{_datadir}/mozilla/extensions/%{firefox_app_id}
%dir %{_libdir}/mozilla/extensions/%{firefox_app_id}
%{_datadir}/applications/mozilla-%{name}.desktop
%dir %{mozappdir}
%doc %{mozappdir}/LICENSE
%doc %{mozappdir}/README.txt
%{mozappdir}/chrome
%{mozappdir}/chrome.manifest
%dir %{mozappdir}/components
%{mozappdir}/components/*.so
%{mozappdir}/components/binary.manifest
%attr(644, root, root) %{mozappdir}/blocklist.xml
%dir %{mozappdir}/extensions
%{mozappdir}/extensions/{972ce4c6-7e08-4474-a285-3208198ce6fd}
%if %{build_langpacks}
%dir %{langpackdir}
%endif
%{mozappdir}/omni.jar
%{mozappdir}/icons
%{mozappdir}/searchplugins
%{mozappdir}/run-mozilla.sh
%{mozappdir}/application.ini
%exclude %{mozappdir}/removed-files
%{_datadir}/icons/hicolor/16x16/apps/%{name}.png
%{_datadir}/icons/hicolor/22x22/apps/%{name}.png
%{_datadir}/icons/hicolor/24x24/apps/%{name}.png
%{_datadir}/icons/hicolor/256x256/apps/%{name}.png
%{_datadir}/icons/hicolor/32x32/apps/%{name}.png
%{_datadir}/icons/hicolor/48x48/apps/%{name}.png

%if %{include_debuginfo}
#%{mozappdir}/crashreporter
%{mozappdir}/crashreporter-override.ini
#%{mozappdir}/Throbber-small.gif
#%{mozappdir}/plugin-container
%endif

#---------------------------------------------------------------------

%changelog
* Tue Jul 19 2011 Arkady L. Shane <ashejn@russianfedora.ru> - 5.0-1.el6.R
- rebuilt for RERemix

* Fri Jun 24 2011 Remi Collet <RPMS@FamilleCollet.com> - 5.0-1
- sync with f15/rawhide
- update to 5.0 finale

* Tue Jun 21 2011 Martin Stransky <stransky@redhat.com> - 5.0-1
- Update to 5.0

* Thu Jun 16 2011 Remi Collet <RPMS@FamilleCollet.com> - 5.0-0.6.build1
- Update to 5.0 build 1 candidate

* Wed Jun 15 2011 Remi Collet <RPMS@FamilleCollet.com> - 5.0-0.5.beta7.build1
- fix windows title

* Wed Jun 15 2011 Remi Collet <RPMS@FamilleCollet.com> - 5.0-0.4.beta7.build1
- update to 5.0 Beta 7 Build 1 Candidate

* Tue Jun 14 2011 Remi Collet <RPMS@FamilleCollet.com> - 5.0-0.3.beta6.build1
- update to 5.0 Beta 6 Build 1 Candidate

* Sun Jun 12 2011 Remi Collet <RPMS@FamilleCollet.com> - 5.0-0.2.b5.build1
- fix desktop file

* Sun Jun 12 2011 Remi Collet <RPMS@FamilleCollet.com> - 5.0-0.1.b5.build1
- patch from spot
- Update to 5.0b5 build1

* Thu Jun  2 2011 Tom Callaway <spot@fedoraproject.org> - 5.0-0.1.b3
- firefox5, b3

* Tue May 10 2011 Martin Stransky <stransky@redhat.com> - 4.0.1-2
- Fixed rhbz#676183 - "firefox -g" is broken

* Thu Apr 28 2011 Remi Collet <RPMS@FamilleCollet.com> - 4.0.1-1
- Update to 4.0.1
- pull latest changes from rawhide

* Thu Apr 21 2011 Christopher Aillon <caillon@redhat.com> - 4.0-4
- Spec file cleanups

* Sun Apr 17 2011 Remi Collet <RPMS@FamilleCollet.com> - 4.0.1-0.1.build1
- Update to 4.0.1 build1 candidate

* Mon Apr  4 2011 Christopher Aillon <caillon@redhat.com> - 4.0-3
- Updates for NetworkManager 0.9
- Updates for GNOME 3

* Tue Mar 22 2011 Christopher Aillon <caillon@redhat.com> - 4.0-2
- Rebuild

* Tue Mar 22 2011 Christopher Aillon <caillon@redhat.com> - 4.0-1
- Firefox 4

* Tue Mar 22 2011 Remi Collet <RPMS@FamilleCollet.com> - 4.0-1
- Firefox 4.0 Finale

* Sat Mar 19 2011 Remi Collet <RPMS@FamilleCollet.com> - 4.0-0.29.rc2
- Firefox 4.0 Release Candidate 2

* Fri Mar 18 2011 Christopher Aillon <caillon@redhat.com> - 4.0-0.21
- Firefox 4.0 RC 2

* Thu Mar 17 2011 Jan Horak <jhorak@redhat.com> - 4.0-0.20
- Rebuild against xulrunner with disabled gnomevfs and enabled gio

* Sat Mar 10 2011 Remi Collet <RPMS@FamilleCollet.com> - 4.0-0.28.rc1
- Firefox 4.0 Release Candidate 1

* Wed Mar  9 2011 Christopher Aillon <caillon@redhat.com> - 4.0-0.19
- Firefox 4.0 RC 1

* Sat Mar 05 2011 Remi Collet <RPMS@FamilleCollet.com> - 4.0-0.27.rc1.build1
- Firefox 4.0 RC1 build1 candidate

* Mon Feb 28 2011 Remi Collet <RPMS@FamilleCollet.com> - 4.0-0.26.beta12
- sync with rawhide
- Firefox 4.0 Beta 12

* Sat Feb 26 2011 Christopher Aillon <caillon@redhat.com> - 4.0-0.18b12
- Switch to using the omni chrome file format

* Fri Feb 25 2011 Christopher Aillon <caillon@redhat.com> - 4.0-0.17b12
- Firefox 4.0 Beta 12

* Wed Feb 23 2011 Remi Collet <RPMS@FamilleCollet.com> - 4.0-0.25.beta12.build1
- sync with rawhide
- Firefox 4.0 Beta 12 build1 candidate

* Thu Feb 10 2011 Christopher Aillon <caillon@redhat.com> - 4.0-0.16b11
- Update gecko-{libs,devel} requires

* Wed Feb 09 2011 Remi Collet <RPMS@FamilleCollet.com> - 4.0-0.24.beta11
- Firefox 4.0 Beta 11

* Tue Feb 08 2011 Christopher Aillon <caillon@redhat.com> - 4.0-0.15b11
- Firefox 4.0 Beta 11

* Fri Feb 04 2011 Remi Collet <RPMS@FamilleCollet.com> - 4.0-0.23.beta11.build3
- 4.0b11 build3 candidate

* Thu Feb 03 2011 Remi Collet <RPMS@FamilleCollet.com> - 4.0-0.22.beta11.build2
- 4.0b11 build2 candidate

* Wed Feb 02 2011 Remi Collet <RPMS@FamilleCollet.com> - 4.0-0.21.beta10
- sync with rawhide, use system xulrunner2

* Tue Jan 25 2011 Christopher Aillon <caillon@redhat.com> - 4.0-0.13b10
- Firefox 4.0 Beta 10

* Fri Jan 14 2011 Christopher Aillon <caillon@redhat.com> - 4.0-0.12b9
- Firefox 4.0 Beta 9

* Thu Jan 6 2011 Dan Horák <dan[at]danny.cz> - 4.0-0.11b8
- disable ipc on non-x86 arches to match xulrunner

* Thu Jan 6 2011 Martin Stransky <stransky@redhat.com> - 4.0-0.10b8
- application.ini permission check fix

* Thu Jan 6 2011 Martin Stransky <stransky@redhat.com> - 4.0-0.9b8
- Fixed rhbz#667477 - broken launch script

* Tue Jan 4 2011 Martin Stransky <stransky@redhat.com> - 4.0-0.8b8
- Fixed rhbz#664877 - Cannot read application.ini

* Tue Dec 21 2010 Martin Stransky <stransky@redhat.com> - 4.0-0.7b8
- Update to Beta 8
- Fixed rhbz#437608 - When prelink is installed, 
  rpm builds are garbage

* Wed Dec  8 2010 Christopher Aillon <caillon@redhat.com> - 4.0-0.6b7
- Use official branding since this is an official beta
- Fix Tab Candy/Panorama (#658573)

* Thu Nov 11 2010 Jan Horak <jhorak@redhat.com> - 4.0b7-1
- Update to 4.0b7
- Added x-scheme-handler to firefox.desktop

* Wed Sep 29 2010 jkeating - 4.0-0.4b6
- Rebuilt for gcc bug 634757

* Tue Sep 21 2010 Martin Stransky <stransky@redhat.com> - 4.0-0.3.b6
- Update to 4.0 Beta 6

* Tue Sep  7 2010 Tom "spot" Callaway <tcallawa@redhat.com> - 4.0-0.2.b4
- get package building and mostly functional

* Mon Aug 30 2010 Martin Stransky <stransky@redhat.com> - 4.0-0.1.b4
- Update to 4.0 Beta 4

