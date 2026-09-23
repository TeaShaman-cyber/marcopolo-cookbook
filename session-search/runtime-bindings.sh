#!/bin/sh

session_search_load_runtime() {
	runtime_env=$1
	[ -r "$runtime_env" ] || return 0

	_ss_corpus_set=${SESSION_SEARCH_CORPUS+x}
	_ss_corpus=${SESSION_SEARCH_CORPUS-}
	_ss_impl_root_set=${SESSION_SEARCH_IMPLEMENTATION_ROOT+x}
	_ss_impl_root=${SESSION_SEARCH_IMPLEMENTATION_ROOT-}
	_ss_impl_head_set=${SESSION_SEARCH_IMPLEMENTATION_HEAD+x}
	_ss_impl_head=${SESSION_SEARCH_IMPLEMENTATION_HEAD-}
	_ss_impl_ref_set=${SESSION_SEARCH_IMPLEMENTATION_REF+x}
	_ss_impl_ref=${SESSION_SEARCH_IMPLEMENTATION_REF-}
	_ss_canonical_dir_set=${SESSION_SEARCH_CANONICAL_DIR+x}
	_ss_canonical_dir=${SESSION_SEARCH_CANONICAL_DIR-}

	set -a
	. "$runtime_env"
	set +a

	if [ "$_ss_corpus_set" = x ]; then
		SESSION_SEARCH_CORPUS=$_ss_corpus
		export SESSION_SEARCH_CORPUS
	fi
	if [ "$_ss_impl_root_set" = x ]; then
		SESSION_SEARCH_IMPLEMENTATION_ROOT=$_ss_impl_root
		export SESSION_SEARCH_IMPLEMENTATION_ROOT
	fi
	if [ "$_ss_impl_head_set" = x ]; then
		SESSION_SEARCH_IMPLEMENTATION_HEAD=$_ss_impl_head
		export SESSION_SEARCH_IMPLEMENTATION_HEAD
	fi
	if [ "$_ss_impl_ref_set" = x ]; then
		SESSION_SEARCH_IMPLEMENTATION_REF=$_ss_impl_ref
		export SESSION_SEARCH_IMPLEMENTATION_REF
	fi
	if [ "$_ss_canonical_dir_set" = x ]; then
		SESSION_SEARCH_CANONICAL_DIR=$_ss_canonical_dir
		export SESSION_SEARCH_CANONICAL_DIR
	fi

	unset _ss_corpus_set _ss_corpus _ss_impl_root_set _ss_impl_root
	unset _ss_impl_head_set _ss_impl_head _ss_impl_ref_set _ss_impl_ref
	unset _ss_canonical_dir_set _ss_canonical_dir
}
