package main

import "C"

import (
	"bytes"
	"fmt"
	"regexp"
	"strings"
	"text/template"
	"unsafe"

	"github.com/Masterminds/sprig/v3"
	"helm.sh/helm/v3/pkg/action"
	"helm.sh/helm/v3/pkg/chart/loader"
	"helm.sh/helm/v3/pkg/cli"
	"helm.sh/helm/v3/pkg/cli/values"
	"helm.sh/helm/v3/pkg/getter"
	"k8s.io/apimachinery/pkg/util/validation"
)

const defaultDirectoryPermission_c = 0755

var (
	whitespaceRegex_c = regexp.MustCompile(`^\s*$`)
)

// generates name using Sprig template
func generateName(nameTemplate string) (string, error) {
	t, err := template.New("name-template").Funcs(sprig.TxtFuncMap()).Parse(nameTemplate)
	if err != nil {
		return "", err
	}
	var b bytes.Buffer
	err = t.Execute(&b, nil)
	if err != nil {
		return "", err
	}
	return b.String(), nil
}

//export renderChart
func renderChart(c_chartpath, c_outputDir, c_valueFile, c_namespace, c_releaseName, c_nameTemplate *C.char, c_valuesFiles **C.char, c_valuesFilesSize C.int) *C.char {
	chartPath := C.GoString(c_chartpath)
	outputDir := C.GoString(c_outputDir)
	valueFile := C.GoString(c_valueFile)
	// values in YAML file
	var valueFiles []string
	if valueFile != "" {
		valueFiles = append(valueFiles, valueFile)
	}

	// https://stackoverflow.com/questions/47354663/access-c-array-of-type-const-char-from-go
	size := int(c_valuesFilesSize)
	cStrings := (*[1 << 30]*C.char)(unsafe.Pointer(c_valuesFiles))[:size:size]
	for _, cString := range cStrings {
		valueFiles = append(valueFiles, C.GoString(cString))
	}

	nameTemplate := C.GoString(c_nameTemplate)
	releaseName := C.GoString(c_releaseName) // will be overwritten by nameTemplate if set
	namespace := C.GoString(c_namespace)

	valueOpts := &values.Options{
		ValueFiles: valueFiles,
	}

	settings := cli.New()
	p := getter.All(settings)
	vals, err := valueOpts.MergeValues(p)
	if err != nil {
		return C.CString(err.Error())
	}

	// If template is specified, try to run the template.
	if nameTemplate != "" {
		releaseName, err = generateName(nameTemplate)
		if err != nil {
			return C.CString(err.Error())
		}
	}

	chart, err := loader.Load(chartPath)
	if err != nil {
		return C.CString(err.Error())
	}

	if releaseName == "" {
		releaseName = chart.Metadata.Name
	}
	if msgs := validation.IsDNS1123Subdomain(releaseName); len(msgs) > 0 {
		return C.CString(fmt.Errorf("release name %s is invalid: %s", releaseName, strings.Join(msgs, ";")).Error())
	}

	actionConfig := new(action.Configuration)
	client := action.NewInstall(actionConfig)
	client.DryRun = true
	client.ReleaseName = releaseName
	client.Namespace = namespace
	client.Replace = true // Skip the name check
	client.ClientOnly = true
	client.IncludeCRDs = true
	client.IsUpgrade = false
	client.OutputDir = outputDir

	_, err = client.Run(chart, vals)
	if err != nil {
		return C.CString(err.Error())
	}

	return C.CString("") // return empty string if no error
}

// this is required to build this as shared object file using cgo
func main() {}
