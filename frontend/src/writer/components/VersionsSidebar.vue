<!-- Derived from frappe/suite@df7f341 (frontend/src/apps/writer)/components/VersionsSidebar.vue. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md. -->
<template>
  <div
    class="bg-surface-gray-2 text-ink-gray-8 p-3 text-base flex justify-between items-center select-none"
  >
    <div class="flex flex-col gap-1">
      <div v-if="!versionPreview">
        <span class="text-ink-gray-6">{{ __('You are viewing the version history of') }}</span>
        {{ file.doc.file_name }}
      </div>
      <div v-else-if="versionPreview[0].manual">
        <span class="font-medium">{{ versionPreview[0].title }}</span>
      </div>
      <div v-else>
        {{ __('This is an automatic snapshot of this document from {0}.', [formatStamp(versionPreview[0].title)]) }}
      </div>
      <div class="text-xs text-ink-gray-5">{{ __('Editing is disabled until you exit.') }}</div>
    </div>
    <div class="flex gap-2">
      <Button
        variant="ghost"
        :label="__('Exit')"
        class="hover:!bg-surface-gray-2 hover:underline"
        @click="showVersions = false"
      />
      <Button
        v-if="versionPreview"
        variant="solid"
        :label="__('Restore')"
        @click="restore(versionPreview[0])"
      />
    </div>
  </div>
  <div class="flex h-full overflow-hidden">
    <div class="self-stretch w-72 border-e h-full relative flex flex-col">
      <div class="flex flex-col items-center w-full shrink-0">
        <!-- One: Automatic in a context, since frappe's Automatic is another word in Arabic -->
        <Tabs
          v-model="tab"
          class="w-full"
          as="div"
          :tabs="[
            { value: 'automatic', label: __('Automatic', null, 'Versions taken while writing') },
            { value: 'manual', label: __('Manual') },
          ]"
        />
        <Button
          :icon="LucideX"
          variant="ghost"
          class="absolute right-1 top-2"
          @click="showVersions = false"
        />
      </div>
      <div class="p-3.5 gap-4 flex flex-col flex-1 min-h-0 overflow-y-auto">
        <Button
          v-if="tab === 'manual'"
          :icon="LucidePlus"
          class="absolute right-3 bottom-3"
          variant="outline"
          @click="
            () =>
              createDialog({
                title: __('Create Version'),
                size: 'sm',
                component: h(NewVersionDialog, {
                  data: editor.getHTML(),
                  document,
                }),
              })
          "
        />
        <div
          v-if="
            !Object.entries(groupedVersions).length || !Object.entries(groupedVersions)[0][1].length
          "
          class="text-ink-gray-5 text-sm text-center mt-1"
        >
          {{ __('None yet.') }}
        </div>
        <div
          v-for="[title, group] in Object.entries(groupedVersions)"
          v-else
          :key="title"
          class="flex flex-col gap-1 mb-2 justify-start bg-surface-base"
        >
          <div v-if="title !== 'Manual'" class="text-ink-gray-5 text-sm font-medium mb-1 my-2">
            {{ title }}
          </div>
          <div :class="tab === 'manual' ? 'flex flex-col gap-0.5' : 'grid grid-cols-3 gap-0.5'"><!-- One: a name gets the whole row -->
            <Button
              v-for="(version, i) in group"
              :key="version.name"
              :variant="version.name === versionPreview?.[0]?.name ? 'solid' : 'ghost'"
              class="text-start text-sm py-4"
              :label="version.manual ? version.title : formatDate(version.title).split(', ')[1]"
              @click="
                version.name === versionPreview?.[0]?.name
                  ? (versionPreview = null)
                  : (versionPreview = [version, getPrevious(version)])
              "
            />
          </div>
        </div>
      </div>
    </div>
    <div class="flex-1 overflow-hidden">
      <div v-if="!versionPreview" class="text-base border-b text-ink-gray-8 p-3 select-none">
        {{ __('This is the current version.') }}
      </div>
      <!-- One: this frappe-ui's Editor draws no element of its own, so its classes go on a div -->
      <div class="h-full overflow-y-auto">
      <div class="diff-view prose prose-sm md:min-w-[48rem] md:max-w-[48rem] mx-auto py-8 px-10">
      <Editor
        v-if="editor?.getHTML"
        :extensions="[RichTextKit, ...COMMON_EXTENSIONS, DiffTag]"
        :editable="false"
        :model-value="
          versionPreview
            ? generateHTMLDiff(versionPreview[0]?.snapshot, versionPreview[1]?.snapshot)
            : generateHTMLDiff(editor.getHTML(), versions.data[versions.data.length - 1]?.snapshot)
        "
      >
        <template #default="{ editor }">
          <EditorContent
            class="prose-sm prose-v3"
            :style="{
              fontFamily: `var(--font-${settings?.font_family})`,
              fontSize: `${settings?.font_size || 15}px`,
              lineHeight: cssLineHeight(settings?.line_height),
            }"
            :editor
          />
        </template>
      </Editor>
      </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import { COMMON_EXTENSIONS } from '@/apps/writer/utils'
import { cssLineHeight } from '@/apps/writer/utils/typography'
import { diff_match_patch } from 'diff-match-patch'
import DiffTag from '@/apps/writer/extensions/diff-tag'
const dmp = new diff_match_patch()

function generateHTMLDiff(newHTML, oldHTML = '') {
  const parser = new DOMParser()
  const oldDoc = parser.parseFromString(oldHTML, 'text/html').body
  const newDoc = parser.parseFromString(newHTML, 'text/html').body

  const result = diffNode(oldDoc, newDoc)
  return result.map((node) => (typeof node === 'string' ? node : node.outerHTML)).join('')
}

function diffNode(oldNode, newNode) {
  // if both missing
  if (!oldNode && !newNode) return []

  // node removed
  if (oldNode && !newNode)
    return [`<del>${oldNode.outerHTML || escapeHTML(oldNode.textContent)}</del>`]

  // node added
  if (!oldNode && newNode)
    return [`<ins>${newNode.outerHTML || escapeHTML(newNode.textContent)}</ins>`]

  // different node type or tag
  if (oldNode.nodeName !== newNode.nodeName) {
    return [
      `<del>${oldNode.outerHTML || escapeHTML(oldNode.textContent)}</del>`,
      `<ins>${newNode.outerHTML || escapeHTML(newNode.textContent)}</ins>`,
    ]
  }

  // text node diff
  if (oldNode.nodeType === Node.TEXT_NODE && newNode.nodeType === Node.TEXT_NODE) {
    const diffs = dmp.diff_main(oldNode.textContent, newNode.textContent)
    dmp.diff_cleanupSemantic(diffs)
    return diffs.map(([type, text]) => {
      switch (type) {
        case -1:
          return `<del>${escapeHTML(text)}</del>`
        case 1:
          return `<ins>${escapeHTML(text)}</ins>`
        default:
          return escapeHTML(text)
      }
    })
  }

  // recursively diff children
  const resultNode = newNode.cloneNode(false)
  const oldChildren = [...oldNode.childNodes]
  const newChildren = [...newNode.childNodes]
  const len = Math.max(oldChildren.length, newChildren.length)

  for (let i = 0; i < len; i++) {
    const childDiff = diffNode(oldChildren[i], newChildren[i])
    childDiff.forEach((fragment) => {
      if (typeof fragment === 'string') {
        const span = document.createElement('span')
        span.innerHTML = fragment
        resultNode.append(...span.childNodes)
      } else {
        resultNode.append(fragment)
      }
    })
  }

  return [resultNode]
}

function escapeHTML(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

import LucideX from '~icons/lucide/x'
import LucidePlus from '~icons/lucide/plus'
import { onKeyDown } from '@vueuse/core'
import { computed, ref, h, watch, inject } from 'vue'
import emitter from '@/apps/writer/emitter'
import { Button, createResource, Tabs, toast } from 'frappe-ui'
import { Editor, EditorContent, RichTextKit } from 'frappe-ui/editor'
import { clearDialogs, createDialog } from '@/apps/writer/utils/dialogs'
import NewVersionDialog from './NewVersionDialog.vue'
import { __ } from '../../kit/desk' // One: the desk's translations
import { formatDate } from '@/apps/writer/utils/format' // One: the workspace's date and time formats

const props = defineProps({
  settings: Object,
  document: Object,
  editor: Object,
})
const emit = defineEmits(['saveDocument', 'newVersion'])
const versionPreview = defineModel()
const showVersions = defineModel('showVersions')

const file = inject('file')
const versions = createResource({
  url: 'onedesk.one_doc.versions.listed', // One: the history through one_doc/versions.py
  params: { id: file.doc.name },
  cache: ['versions', file.doc?.name],
  initialData: [],
  auto: true,
})

const manualVersions = computed(() => versions.data.filter((v) => v.manual))
const autoVersions = computed(() => versions.data.filter((v) => !v.manual))

const formatStamp = (dateStr) => formatDate(dateStr).replace(', ', ' ')

const groupedVersions = computed(() => {
  if (tab.value === 'automatic') {
    const sortedAutoVersions = [...autoVersions.value].sort((a, b) => {
      return new Date(b.title) - new Date(a.title)
    })

    const grouped = sortedAutoVersions.reduce((acc, version) => {
      const date = formatDate(version.title).split(', ')[0]
      if (!acc[date]) {
        acc[date] = []
      }
      acc[date].push(version)
      return acc
    }, {})

    return grouped
  } else {
    return {
      Manual: [...manualVersions.value].sort((a, b) => {
          return new Date(b.creation) - new Date(a.creation) // One: a named version's title is not a date
      }),
    }
  }
})

const tab = ref(versions.data.filter((v) => v.manual).length ? 'manual' : 'automatic')
watch(tab, () => (versionPreview.value = null))

const getPrevious = (version) => {
  // Important: Use the original arrays, not the reversed ones
  const relevantVersions = version.manual
    ? versions.data.filter((v) => v.manual)
    : versions.data.filter((v) => !v.manual)
  const currentIndex = relevantVersions.findIndex((v) => v.name === version.name)
  return relevantVersions[currentIndex - 1]
}

const restore = (version) => {
  createDialog({
    title: __('Restore this version?'),
    size: 'sm',
    message: version.manual
      ? __('You are restoring to a previous version: {0}.', [version.title])
      : __('You are restoring the document to how it was at {0}.', [formatStamp(version.title)]),
    actions: [
      {
        label: __('Restore'),
        variant: 'solid',
        onClick: () => {
          props.editor.commands.setContent(version.snapshot)
          toast.success(
            __('Restored {0}', [version.manual ? version.title : formatStamp(version.title)]),
          )
          showVersions.value = false
          clearDialogs()
          emitter.emit('manual-save')
        },
      },
    ],
  })
}
onKeyDown('Escape', () => (showVersions.value = false))
</script>
<style>
@import url('../styles/fonts.css'); /* One: relative, CSS imports resolve no aliases here */

.diff-view ins,
.diff-view s {
  padding: 0.5px 1px;
  border-radius: 3px;
}

.diff-view ins + s,
.diff-view s + ins {
  margin: 0 2px;
}

.diff-view ins {
  background-color: #dcfce7;
  color: #166534;
  text-decoration: none;
}

.diff-view s {
  background-color: #fee2e2;
  color: #991b1b;
  text-decoration: line-through;
}
</style>
