package main

import "C"

import (
	"bytes"
	"fmt"
	"github.com/Masterminds/sprig"
	"github.com/ghodss/yaml"
	"io/ioutil"
	"k8s.io/apimachinery/pkg/util/validation"
	"k8s.io/helm/pkg/chartutil"
	"k8s.io/helm/pkg/manifest"
	"k8s.io/helm/pkg/proto/hapi/chart"
	"k8s.io/helm/pkg/renderutil"
	"k8s.io/helm/pkg/strvals"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"strings"
	"text/template"
)

const defaultDirectoryPermission_c = 0755

var (
	whitespaceRegex_c = regexp.MustCompile(`^\s*$`)
	// defaultKubeVersion is the default value of --kube-version flag
	defaultKubeVersion_c = fmt.Sprintf("%s.%s", chartutil.DefaultKubeVersion.Major, chartutil.DefaultKubeVersion.Minor)
)

// copied from install.go
type valueFiles []string

func (v *valueFiles) String() string {
	return fmt.Sprint(*v)
}

func (v *valueFiles) Type() string {
	return "valueFiles"
}

func (v *valueFiles) Set(value string) error {
	for _, filePath := range strings.Split(value, ",") {
		*v = append(*v, filePath)
	}
	return nil
}

//readFile load a file from the local directory. remote file is disabled.
func readFile(filePath string) ([]byte, error) {
	return ioutil.ReadFile(filePath)
}

// Merges source and destination map, preferring values from the source map
func mergeValues(dest map[string]interface{}, src map[string]interface{}) map[string]interface{} {
	for k, v := range src {
		// If the key doesn't exist already, then just set the key to that value
		if _, exists := dest[k]; !exists {
			dest[k] = v
			continue
		}
		nextMap, ok := v.(map[string]interface{})
		// If it isn't another map, overwrite the value
		if !ok {
			dest[k] = v
			continue
		}
		// Edge case: If the key exists in the destination, but isn't a map
		destMap, isMap := dest[k].(map[string]interface{})
		// If the source map has a map for this key, prefer it
		if !isMap {
			dest[k] = v
			continue
		}
		// If we got to this point, it is a map in both, so merge them
		dest[k] = mergeValues(destMap, nextMap)
	}
	return dest
}

// vals merges values from files specified via -f/--values and
// directly via --set or --set-string or --set-file, marshaling them to YAML
func vals(valueFiles valueFiles, values []string, stringValues []string, fileValues []string) ([]byte, error) {
	base := map[string]interface{}{}

	// User specified a values files via -f/--values
	for _, filePath := range valueFiles {
		currentMap := map[string]interface{}{}

		var bytes []byte
		var err error
		if strings.TrimSpace(filePath) == "-" {
			bytes, err = ioutil.ReadAll(os.Stdin)
		} else {
			bytes, err = readFile(filePath)
		}

		if err != nil {
			return []byte{}, err
		}

		if err := yaml.Unmarshal(bytes, &currentMap); err != nil {
			return []byte{}, fmt.Errorf("failed to parse %s: %s", filePath, err)
		}
		// Merge with the previous map
		base = mergeValues(base, currentMap)
	}

	// User specified a value via --set
	for _, value := range values {
		if err := strvals.ParseInto(value, base); err != nil {
			return []byte{}, fmt.Errorf("failed parsing --set data: %s", err)
		}
	}

	// User specified a value via --set-string
	for _, value := range stringValues {
		if err := strvals.ParseIntoString(value, base); err != nil {
			return []byte{}, fmt.Errorf("failed parsing --set-string data: %s", err)
		}
	}

	// User specified a value via --set-file
	for _, value := range fileValues {
		reader := func(rs []rune) (interface{}, error) {
			bytes, err := readFile(string(rs))
			return string(bytes), err
		}
		if err := strvals.ParseIntoFile(value, base, reader); err != nil {
			return []byte{}, fmt.Errorf("failed parsing --set-file data: %s", err)
		}
	}

	return yaml.Marshal(base)
}

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
func renderChart(c_chartpath, c_outputDir, c_valueFile, c_namespace, c_releaseName, c_nameTemplate *C.char) *C.char {
	chartPath := C.GoString(c_chartpath)
	outputDir := C.GoString(c_outputDir)
	valueFile := C.GoString(c_valueFile)
	// values in YAML file
	var valueFiles []string
	if valueFile != "" {
		valueFiles = append(valueFiles, valueFile)
	}
	var values []string
	// to force string values
	var stringValues []string
	var fileValues []string
	nameTemplate := C.GoString(c_nameTemplate)
	releaseName := C.GoString(c_releaseName) // will be overwritten by nameTemplate if set
	namespace := C.GoString(c_namespace)
	kubeVersion := defaultKubeVersion_c
	// particular template files to render
	var renderFiles []string
	showNotes := false

	rawVals, err := vals(valueFiles, values, stringValues, fileValues)
	if err != nil {
		return C.CString(err.Error())
	}
	config := &chart.Config{Raw: string(rawVals), Values: map[string]*chart.Value{}}

	// If template is specified, try to run the template.
	if nameTemplate != "" {
		releaseName, err = generateName(nameTemplate)
		if err != nil {
			return C.CString(err.Error())
		}
	}

	if msgs := validation.IsDNS1123Subdomain(releaseName); releaseName != "" && len(msgs) > 0 {
		return C.CString(fmt.Errorf("release name %s is invalid: %s", releaseName, strings.Join(msgs, ";")).Error())
	}

	// Check chart requirements to make sure all dependencies are present in /charts
	c, err := chartutil.Load(chartPath)
	if err != nil {
		return C.CString(err.Error())
	}

	renderOpts := renderutil.Options{
		ReleaseOptions: chartutil.ReleaseOptions{
			Name:      releaseName,
			IsInstall: true,
			IsUpgrade: false,
			Time:      nil,
			Namespace: namespace,
		},
		KubeVersion: kubeVersion,
	}

	renderedTemplates, err := renderutil.Render(c, config, renderOpts)
	if err != nil {
		return C.CString(err.Error())
	}

	listManifests := manifest.SplitManifests(renderedTemplates)
	var manifestsToRender []manifest.Manifest

	// if we have a list of files to render, then check that each of the
	// provided files exists in the chart.
	if len(renderFiles) > 0 {
		for _, f := range renderFiles {
			missing := true
			if !filepath.IsAbs(f) {
				newF, err := filepath.Abs(filepath.Join(chartPath, f))
				if err != nil {
					C.CString(fmt.Errorf("could not turn template path %s into absolute path: %s", f, err).Error())
				}
				f = newF
			}

			for _, manifest := range listManifests {
				// manifest.Name is rendered using linux-style filepath separators on Windows as
				// well as macOS/linux.
				manifestPathSplit := strings.Split(manifest.Name, "/")
				// remove the chart name from the path
				manifestPathSplit = manifestPathSplit[1:]
				toJoin := append([]string{chartPath}, manifestPathSplit...)
				manifestPath := filepath.Join(toJoin...)

				// if the filepath provided matches a manifest path in the
				// chart, render that manifest
				if f == manifestPath {
					manifestsToRender = append(manifestsToRender, manifest)
					missing = false
				}
			}
			if missing {
				return C.CString(fmt.Errorf("could not find template %s in chart", f).Error())
			}
		}
	} else {
		// no renderFiles provided, render all manifests in the chart
		manifestsToRender = listManifests
	}

	for _, m := range manifestsToRender {
		data := m.Content
		b := filepath.Base(m.Name)
		if !showNotes && b == "NOTES.txt" {
			continue
		}
		if strings.HasPrefix(b, "_") {
			continue
		}

		if outputDir != "" {
			// blank template after execution
			if whitespaceRegex_c.MatchString(data) {
				continue
			}
			err = writeToFile_c(outputDir, m.Name, data)
			if err != nil {
				C.CString(err.Error())
			}
			continue
		}
		fmt.Printf("---\n# Source: %s\n", m.Name)
		fmt.Println(data)
	}
	return C.CString("") // return empty string if no error
}

// write the <data> to <output-dir>/<name>
func writeToFile_c(outputDir string, name string, data string) error {
	outfileName := strings.Join([]string{outputDir, name}, string(filepath.Separator))
	err := ensureDirectoryForFile_c(outfileName)
	if err != nil {
		return err
	}

	f, err := os.Create(outfileName)
	if err != nil {
		return err
	}

	defer f.Close()

	_, err = f.WriteString(fmt.Sprintf("---\n# Source: %s\n%s", name, data))

	if err != nil {
		return err
	}

	return nil
}

// check if the directory exists to create file. creates if don't exists
func ensureDirectoryForFile_c(file string) error {
	baseDir := path.Dir(file)
	_, err := os.Stat(baseDir)
	if err != nil && !os.IsNotExist(err) {
		return err
	}

	return os.MkdirAll(baseDir, defaultDirectoryPermission_c)
}

// this is required to build this as shared object file using cgo
func main() {}
